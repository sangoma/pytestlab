import logging
from ..config import load_yaml_config
from .common import ProviderError
from .files import FileProvider
from .etcd import EtcdProvider
from .postgresql import PostgresqlProvider


log = logging.getLogger(__name__)


class ProviderManager(object):
    """Manage environment provider backends.
    """
    types = {
        'files': FileProvider,
        'etcd': EtcdProvider,
        'postgresql': PostgresqlProvider,
    }

    @classmethod
    def add(cls, name, storetype):
        if name in cls.types:
            log.warn("Overwriting {} store with {}".format(
                name, storetype))

        cls.types[name] = storetype

    @classmethod
    def get(cls, name):
        return cls.types.get(name)


def load_stores(args):
    """Load data store instances (stores) for each provider name and args
    in ``args``.
    """
    providers = []
    for name, configdict in args:
        log.debug("Found provider entry {}".format(name))
        provider = ProviderManager.types[name](configdict)  # create instance
        providers.append(provider)
    return providers


def get_providers(targets=None, yamlconf=None, pytestconfig=None):
    if isinstance(targets, str):
        # parse `targets` comma separated str
        targets = set(x.strip() for x in targets.split(','))

    provider_args = []
    yamlconf = yamlconf or load_yaml_config()
    if pytestconfig and pytestconfig.option.env != 'anonymous' or targets:
        assert yamlconf, 'No config file (lab.yaml) could be found?'
        for node in yamlconf.get('providers'):
            name, configdict = node.items()[0]
            if not targets or name in targets:
                provider_args.append((name, configdict))

    if pytestconfig:
        for name, configdict in pytestconfig.hook.pytest_lab_add_providers(
            config=pytestconfig,
            providermanager=ProviderManager
        ):
            if name:
                provider_args.append((name, configdict))

    return load_stores(provider_args)
