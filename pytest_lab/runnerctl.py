#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
pytest runner control plugin
"""
from builtins import object
import string
import signal
import pytest


try:
    maketrans = str.maketrans
except AttributeError:
    maketrans = string.maketrans


def exit_gracefully(signum, frame):
    raise pytest.exit('Interrupting from SIGTERM')


class Halt(object):
    def __init__(self):
        self.msg = None

    def shouldstop(self, msg):
        self.msg = msg

    def __call__(self, msg):
        __tracebackhide__ = True
        self.msg = msg
        pytest.fail(msg)


def pytest_namespace():
    halt = Halt()
    return {'halt': halt,
            'shouldstop': halt.shouldstop}


def pytest_configure(config):
    signal.signal(signal.SIGTERM, exit_gracefully)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    yield
    if pytest.halt.msg:
        item.session.shouldstop = pytest.halt.msg


def pytest_runtest_makereport(item, call):
    if 'setup_test' in item.keywords and call.excinfo:
        if not call.excinfo.errisinstance(pytest.skip.Exception):
            item.session.shouldstop = 'A setup test has failed, aborting...'


@pytest.fixture(scope='class')
def testname(request):
    """Pytest test node name with all unfriendly characters transformed
    into underscores. The lifetime is class scoped since this name is
    often used to provision remote sw profiles which live for the entirety
    of a test suite.
    """
    return request.node.name.translate(maketrans('\[', '__')).strip(']')
