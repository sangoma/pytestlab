import pytest
from lab import utils


class LocalStorage(object):
    def __init__(self, config, rootdir):
        self.config = config
        self.rootdir = rootdir

    @pytest.hookimpl
    def pytest_load_initial_conftests(early_config, parser, args):
        self.rootdir = utils.get_common_ancestor(args)

    @pytest.hookimpl
    def pytest_lab_getcfg(self, config, filenames):
        _, result, _ = utils.getcfg([self.rootdir], filenames)
        return result


@pytest.hookimpl
def pytest_load_initial_conftests(early_config, parser, args):
    rootdir = utils.get_common_ancestor(args)
    early_config.pluginmanager.register(LocalStorage(early_config, rootdir))
