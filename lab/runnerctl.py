#
# Copyright 2017 Sangoma Technologies Inc.
#
"""
pytest runner control plugin
"""
from builtins import object
import pytest
import string


def pytest_runtest_makereport(item, call):
    if 'setup_test' in item.keywords and call.excinfo:
        if not call.excinfo.errisinstance(pytest.skip.Exception):
            pytest.halt('A setup test has failed, aborting...')


class Halt(object):
    def __init__(self):
        self.msg = None

    def __call__(self, msg):
        __tracebackhide__ = True
        self.msg = msg
        pytest.fail(msg)


def pytest_namespace():
    return {'halt': Halt()}


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    yield
    if pytest.halt.msg:
        item.session.shouldstop = pytest.halt.msg


@pytest.fixture(scope='class')
def testname(request):
    """Pytest test node name with all unfriendly characters transformed
    into underscores. The lifetime is class scoped since this name is
    often used to provision remote sw profiles which live for the entirety
    of a test suite.
    """
    return request.node.name.translate(
        string.maketrans('\[', '__')).strip(']')
