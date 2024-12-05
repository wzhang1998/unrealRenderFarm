"""
My custom render executor for remote/distributed rendering
"""

import time
import unreal
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

from util import client
from util import renderRequest


@unreal.uclass()
class MyExecutor(unreal.MoviePipelinePythonHostExecutor):

    pipeline = unreal.uproperty(unreal.MoviePipeline)
    job_id = unreal.uproperty(unreal.Text)

    def _post_init(self):
        """
        The Executor constructor different from the standard __init__()

        Good place to register http callback function
        """
        self.pipeline = None
        self.queue = None
        self.job_id = unreal.Text()  # Initialize with an empty unreal.Text

        self.http_response_recieved_delegate.add_function_unique(
            self,
            "on_http_response_received"
        )
        LOGGER.info("MyExecutor initialized")

    def parse_argument(self):
        """
        Parse commandline arguments that initiated the Executor class
        """
        (cmd_tokens, cmd_switches, cmd_parameters) = unreal.SystemLibrary.\
            parse_command_line(unreal.SystemLibrary.get_command_line())

        self.map_path = cmd_tokens[0]
        self.job_id = unreal.Text(cmd_parameters['JobId'])  # Convert to unreal.Text
        self.seq_path = cmd_parameters['LevelSequence']
        self.preset_path = cmd_parameters['MoviePipelineConfig']
        LOGGER.info(f"Arguments parsed: map_path={self.map_path}, job_id={self.job_id}, seq_path={self.seq_path}, preset_path={self.preset_path}")

    def add_job(self):
        """
        Add job to pipeline queue based off commandline arguments

        :return: unreal.MoviePipelineExecutorJob. new render job
        """
        job = self.queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
        job.map = unreal.SoftObjectPath(self.map_path)
        job.sequence = unreal.SoftObjectPath(self.seq_path)

        preset_path = unreal.SoftObjectPath(self.preset_path)
        u_preset = unreal.SystemLibrary.conv_soft_obj_path_to_soft_obj_ref(preset_path)
        job.set_configuration(u_preset)

        LOGGER.info(f"Job added: {job}")

        return job

    @unreal.ufunction(override=True)
    def execute_delayed(self, queue):
        """
        Function called once level has loaded

        Good place to parse commandline arguments
        We also created a new pipeline and new queue and registered pipeline
        callback

        :param queue: unreal.MoviePipelineQueue.
                      optional. if we want this argument to be valid, we
                      can pass a path to an unreal queue asset via
                      '-MoviePipelineConfig' commandline argument
        """
        LOGGER.info("execute_delayed called")
        self.parse_argument()
        LOGGER.info("Arguments parsed in execute_delayed")

        # render pipeline creation
        try:
            self.pipeline = unreal.new_object(
                self.target_pipeline_class,
                outer=self.get_last_loaded_world(),
                base_type=unreal.MoviePipeline
            )
            LOGGER.info("Pipeline object created")

            self.pipeline.on_movie_pipeline_shot_work_finished_delegate.add_function_unique(
                self,
                "on_job_finished"
            )
            self.pipeline.on_movie_pipeline_work_finished_delegate.add_function_unique(
                self,
                "on_pipeline_finished"
            )
            LOGGER.info("Pipeline delegates added")

        # keep running this even code above has error
        except Exception as e:
        
            # create our own queue for single job handling
            self.queue = unreal.new_object(unreal.MoviePipelineQueue, outer=self)
            job = self.add_job()
            self.pipeline.initialize(job)
            LOGGER.info("Pipeline initialized and job added to queue")
            LOGGER.error(f"Error in execute_delayed: {e}")

    @unreal.ufunction(override=True)
    def on_begin_frame(self):
        """
        Callback function on every frame

        Count down progress and time estimate, and send http request
        to update job status
        """
        super(MyExecutor, self).on_begin_frame()

        if not self.pipeline:
            return

        unreal.log("Progress: %f" % 
                   unreal.MoviePipelineLibrary.get_completion_percentage(self.pipeline))
        
        status = renderRequest.RenderStatus.in_progress
        progress = 100 * unreal.MoviePipelineLibrary.get_completion_percentage(self.pipeline)
        time_estimate = unreal.MoviePipelineLibrary.get_estimated_time_remaining(self.pipeline)
        time_estimate_str = unreal.TextLibrary.as_timespan_timespan(time_estimate)

        if not time_estimate:
            time_estimate = unreal.Text("Unknown")

        LOGGER.info(f"Frame update: progress={progress}, time_estimate={time_estimate}")

        self.send_http_request(
            '{}/put/{}'.format(client.SERVER_API_URL, self.job_id),
            "PUT",
            '{};{};{}'.format(progress, time_estimate_str, status),
            unreal.Map(str, str)
        )

    @unreal.ufunction(ret=None, params=[int, int, str])
    def on_http_response_received(self, index, code, message):
        """
        Http response received callback

        :param index: int. response index that matches the request index
        :param code: int. http response code
        :param message: str. http response message
        """
        if code == 200:
            unreal.log(message)
        else:
            unreal.log_error('something wrong with the server!!')

    @unreal.ufunction(override=True)
    def is_rendering(self):
        """
        Override. whether or not the Render Local/Remote buttons are loacked
        in the editor executor

        :return: bool
        """
        return False

    @unreal.ufunction(ret=None, params=[unreal.MoviePipeline, bool])
    def on_job_finished(self, pipeline, is_errored):
        """
        Render job finished callback

        Since we are process only one job, we update server when it has completed
        and then call on_executor_finished_impl() to end the whole queue

        :param pipeline: unreal.MoviePipeline. pipeline owning the job
        :param is_errored: bool. whether the pipeline errors out
        """
        self.pipeline = None
        unreal.log("Finished rendering movie!")
        self.on_executor_finished_impl()

        time.sleep(1)

        # update to server
        progress = 100
        time_estimate = 'N/A'
        status = renderRequest.RenderStatus.finished
        self.send_http_request(
            '{}/put/{}'.format(client.SERVER_API_URL, self.job_id),
            "PUT",
            '{};{};{}'.format(progress, time_estimate, status),
            unreal.Map(str, str)
        )

    @unreal.ufunction(ret=None, params=[unreal.MoviePipelineOutputData])
    def on_pipeline_finished(self, results):
        """
        Render pipeline/queue finished callback

        :param results: unreal.MoviePipelineOutputData. extensive results
                        of the pipeline output
        """
        output_data = results
        if output_data.success:
            for shot_data in output_data.shot_data:
                render_pass_data = shot_data.render_pass_data
                for k, v in render_pass_data.items():
                    if k.name == 'FinalImage':
                        outputs = v.file_paths
                        # get all final output images
                        # unreal.log(outputs)
