from lab.ssh import get_ssh, get_sftp
from pytest_lab.rpc import Execnet

from .utils import weakref_cache


@weakref_cache
def connect(hostname, **kwargs):
    return get_ssh(hostname, **kwargs)


@weakref_cache
def sftp(hostname, **kwargs):
    return get_sftp(hostname, **kwargs)


@weakref_cache
def execnet(hostname, **kwargs):
    return Execnet(hostname, **kwargs)
