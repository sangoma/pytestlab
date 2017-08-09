import pytest
from lab import config_v1


@pytest.hookimpl
def pytest_addoption(parser):
    group = parser.getgroup('environment')
    group.addoption('--env', action='store')
    group.addoption('--zone', action='store')


@pytest.hookimpl
def pytest_lab_map(config, roles):
    mapfile = config.hook.pytest_lab_getcfg(config=config,
                                            filenames=['map.yaml'])
    if not mapfile:
        return

    mapdata = config_v1.load(mapfile)

    environments, zones = mapdata
    envname = config.getoption('--env')
    zonename = config.getoption('--zone')

    environment = environments.get(envname, {})

    if not zonename:
        env_zones = environment.get('zones')
        if env_zones:
            zonename = env_zones[0]

    zone = zones.get(zonename, {})

    locker = zone.get('locker')
    if locker and locker.get('service') == 'etcd':
        from .locker import EtcdLocker, Locker
        etcd = EtcdLocker(zonename)
        config.pluginmanager.register(Locker(config, etcd))

    roles.load(environment.get('roles', {}),
               zone.get('roles', {}))
