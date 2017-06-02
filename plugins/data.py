from builtins import object
from builtins import str
import py
import py.path
import pytest


def exists(path, ignore=EnvironmentError):
    try:
        return path.check()
    except ignore:
        return False


def get_common_ancestor(args):
    # args are what we get after early command line parsing (usually
    # strings, but can be py.path.local objects as well)
    common_ancestor = None
    for arg in args:
        if str(arg)[0] == "-":
            continue
        p = py.path.local(arg)
        if common_ancestor is None:
            common_ancestor = p
        else:
            if p.relto(common_ancestor) or p == common_ancestor:
                continue
            elif common_ancestor.relto(p):
                common_ancestor = p
            else:
                shared = p.common(common_ancestor)
                if shared is not None:
                    common_ancestor = shared
    if common_ancestor is None:
        common_ancestor = py.path.local()
    elif not common_ancestor.isdir():
        common_ancestor = common_ancestor.dirpath()
    return common_ancestor


class LocalStorage(object):
    def __init__(self, config, rootdir=None):
        self.config = config
        self.rootdir = py.path.local(rootdir) or py.path.local()

    @pytest.hookimpl
    def pytest_lab_getcfg(self, config, filenames):
        for base in self.rootdir.parts(reverse=True):
            for filename in filenames:
                p = base.join(filename)
                if exists(p):
                    return p


@pytest.hookimpl
def pytest_load_initial_conftests(early_config, parser, args):
    rootdir = get_common_ancestor(args)
    early_config.pluginmanager.register(LocalStorage(early_config, rootdir))
