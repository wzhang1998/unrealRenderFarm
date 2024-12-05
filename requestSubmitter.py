"""
Client to submit new render request to server
"""

import logging

from util import client


logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def send(d):
    """
    Send/Submit a new render request

    :param d: dict. a render request serialized as dictionary
    """
    rrequest = client.add_request(d)
    if rrequest:
        LOGGER.info('request %s sent to server', rrequest.uid)


if __name__ == '__main__':
    test_job_a = {
        'name': 'test_render01',
        'owner': 'TEST_SUBMITTER_01',
        'umap_path': '/Game/Maps/LVL_MesaLandscape_small.LVL_MesaLandscape_small',
        'useq_path': '/Game/Cinematics/Sequences/MesaSeqSmallscale/MesaSeqSmallscaleRoot.MesaSeqSmallscaleRoot',
        'uconfig_path': '/Game/Cinematics/Presets/Config_4k.Config_4k'
    }

    test_job_b = {
        'name': 'test_render02',
        'owner': 'TEST_SUBMITTER_02',
        'umap_path': '/Game/Maps/LVL_MesaLandscape_small.LVL_MesaLandscape_small',
        'useq_path': '/Game/Cinematics/Sequences/MesaSeqSmallscale/shot/shot0010/shot0010_02.shot0010_02',
        'uconfig_path': '/Game/Cinematics/Presets/Config_4k.Config_4k'
    }

    for job in [test_job_a, test_job_b]:
        send(job)
