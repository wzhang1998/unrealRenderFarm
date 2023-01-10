import logging
import os
import time
import subprocess

from util import client
from util import renderRequest


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODULE_PATH = os.path.dirname(os.path.abspath(__file__))
WORKER_NAME = 'RENDER_MACHINE_01'
UNREAL_EXE = r'E:\Epic\UE_5.0\Engine\Binaries\Win64\UnrealEditor.exe'
UNREAL_PROJECT = r"E:\Epic\UnrealProjects\SequencerTest\SequencerTest.uproject"


def render(uid, umap_path, useq_path, uconfig_path):
    command = [
        UNREAL_EXE,
        UNREAL_PROJECT,

        umap_path,
        "-JobId={}".format(uid),
        "-LevelSequence={}".format(useq_path),
        "-MoviePipelineConfig={}".format(uconfig_path),

        "-game",
        "-MoviePipelineLocalExecutorClass=/Script/MovieRenderPipelineCore.MoviePipelinePythonHostExecutor",
        "-ExecutorPythonClass=/Engine/PythonTypes.MyExecutor",

        "-windowed",
        "-resX=1280",
        "-resY=720",

        "-StdOut",
        "-FullStdOutLogOutput"
    ]
    env = os.environ.copy()
    env["UE_PYTHONPATH"] = MODULE_PATH
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env
    )
    return proc.communicate()


if __name__ == '__main__':
    logger.info('Starting render worker %s', WORKER_NAME)
    while True:
        rrequests = client.get_all_requests()
        uids = [rrequest.uid for rrequest in rrequests
                if rrequest.worker == WORKER_NAME and
                rrequest.status == renderRequest.RenderStatus.ready_to_start]

        # render blocks main loop
        for uid in uids:
            logger.info('rendering job %s', uid)

            rrequest = renderRequest.RenderRequest.from_db(uid)
            output = render(
                uid,
                rrequest.umap_path,
                rrequest.useq_path,
                rrequest.uconfig_path
            )

            # for debugging
            for line in str(output).split(r'\r\n'):
                if 'LogPython' in line:
                    print(line)

            logger.info("finished rendering job %s", uid)

        # check assigned job every 10 sec after previous job has finished
        time.sleep(10)
        logger.info('current job(s) finished, searching for new job(s)')
