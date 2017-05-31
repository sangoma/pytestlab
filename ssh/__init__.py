from lab.ssh import get_ssh, get_sftp
from .utils import weakref_cache


@weakref_cache
def connect(hostname, **kwargs):
    return get_ssh(hostname, **kwargs)


@weakref_cache
def sftp(hostname, **kwargs):
    return get_sftp(hostname, **kwargs)
