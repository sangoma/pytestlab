import logging
from ..config import load_lab_config
from .common import ProviderError
from .files import FileProvider
from .etcd import EtcdProvider
from .postgresql import PostgresqlProvider


log = logging.getLogger(__name__)


BACKENDS = {backend.name: backend
            for backend in [FileProvider, EtcdProvider,
                            PostgresqlProvider]}


def load_backends(config=None):
    if not config:
        config = load_lab_config().get('providers')

    backends = []
    for node in config:
        log.debug("Found config entry {}".format(node))
        name, kwargs = node.items()[0]
        backend = BACKENDS[name](kwargs)
        backends.append(backend)
    return backends


def get_providers(targets, config):
    backends_config = config.get('providers')
    if not backends_config:
        if targets:  # parse `targets` comma separated str
            targets_set = set(x.strip() for x in targets.split(','))
            backends_config = [{target: None} for target in targets_set]
        else:
            backends_config = [{'files': None}]

    return load_backends(backends_config)
