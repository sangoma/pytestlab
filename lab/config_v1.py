import importlib
from enum import Enum
from ruamel import yaml


class LabConfigError(Exception):
    pass


class Error(Enum):
    unqualified_srv = (
        "ERROR: SRV record has no domain and no default available"
    )
    malformed_srv = (
        "ERROR: malformed SRV record\n\n"
    )
    malformed_role = (
        "ERROR: malformed role name"
    )
    malformed_provider = (
        "ERROR: malformed provider name"
    )
    locationless_role = (
        "ERROR: a hostname or srv record must appear in a role"
    )


class Loader(object):
    def __init__(self, name, kwargs):
        self.key = name
        self.kwargs = dict(kwargs)

    def __call__(self):
        modulepath, _, factory = self.key.rpartition('.')
        module = importlib.import_module(modulepath)

        return getattr(module, factory)(**self.kwargs)


class Union(dict):
    def __init__(self, data, zone=None):
        super(Union, self).__init__(data)
        self.zone = zone

    def __missing__(self, key):
        if self.zone:
            return self.zone[key]
        raise KeyError(key)


def load(config_path):
    with config_path.open() as fp:
        config = yaml.load(fp.read(), yaml.RoundTripLoader)

    envs = dict(_parse_environments(config.get('environments', {})))
    zones = dict(_parse_zones(config.get('zones', {})))
    return envs, zones


def _parse_role(name, yaml, container, domain=None):
    return Loader(name, yaml)


def _parse_provider(name, yaml, container):
    return yaml


def _parse_roles(roles, domain=None):
    data = {}
    for name, descs in roles.items():
        data[name] = {key: _parse_role(key, contents, node, domain=domain)
                      for node in descs
                      for key, contents in node.items()}
    return data


def _parse_providers(providers):
    return {key: _parse_provider(key, contents, node)
            for node in providers
            for key, contents in node.items()}


def _parse_common(yaml, domain=None):
    data = {}
    lock = yaml.get('lock')
    if lock:
        data['lock'] = lock

    zones = yaml.get('zones')
    if zones:
        data['zones'] = zones

    roles = yaml.get('roles')
    if roles:
        data['roles'] = _parse_roles(roles, domain=domain)

    providers = yaml.get('providers')
    if providers:
        data['providers'] = _parse_providers(providers)

    return data


def _parse_zones(config):
    for name, yaml in config.items():
        name_is_domain = len(name.split('.')) > 1
        domain = name if name_is_domain else None
        yield name, _parse_common(yaml, domain)


def _parse_environments(config):
    for name, yaml in config.items():
        yield name, _parse_common(yaml)
