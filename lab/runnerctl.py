"""
pytest runner control plugin
"""
import pytest


def pytest_runtest_makereport(item, call):
    if 'setup_test' in item.keywords and call.excinfo:
        if not call.excinfo.errisinstance(pytest.skip.Exception):
            pytest.halt('A setup test has failed, aborting...')


class Halt(object):
    def __init__(self):
        self.msg = None

    def __call__(self, msg):
        self.msg = msg


def pytest_namespace():
    return {'halt': Halt()}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    yield
    if pytest.halt.msg:
        item.session.shouldstop = pytest.halt.msg