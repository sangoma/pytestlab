import logging
import py.path
import yaml
from .common import ProviderError
from .files import FileProvider
from .etcd import EtcdProvider
from .postgresql import PostgresqlProvider


log = logging.getLogger(__name__)


def load_yaml_config():
    """Load data from the file lab.yaml.

    Start looking in the PWD and return the first file found by successive
    upward steps in the file system.
    """
    path = py.path.local()
    for basename in path.parts(reverse=True):
        configfile = basename.join('lab.yaml')
        if configfile.check():
            return yaml.load(configfile.read())
    return {}


class ProviderManager(object):
    """Manage environment provider backends.
    """
    types = {
        'files': FileProvider,
        'etcd': EtcdProvider,
        'postgresql': PostgresqlProvider,
    }

    @classmethod
    def add_store(cls, name, store):
        if name in cls.stores:
            log.warn("Overwriting {} store with {}".format(
                name, store))

        cls.types[name] = store

    @classmethod
    def get_store(cls, name):
        return cls.types.get(name)


def load_stores(args):
    """Load data store instances (stores) for each provider name and args
    in ``args``.
    """
    providers = []
    for name, kwargs in args:
        log.debug("Found provider entry {}".format(name))
        provider = ProviderManager.types[name](kwargs)  # create instance
        providers.append(provider)
    return providers


def get_providers(targets=None, yamlconf=None):
    if isinstance(targets, str):
        # parse `targets` comma separated str
        targets = set(x.strip() for x in targets.split(','))

    yamlconf = yamlconf or load_yaml_config()
    assert yamlconf, 'No config file (lab.yaml) could be found?'

    provider_args = []
    for node in yamlconf.get('providers'):
        name, kwargs = node.items()[0]
        if not targets or name in targets:
            provider_args.append((name, kwargs))

    return load_stores(provider_args)
