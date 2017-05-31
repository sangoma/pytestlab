#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Original Authors:
#   Tyler Goodlet <tgoodlet@gmail.com>
#   Simon Gomizelj <simon@vodik.xyz>
#
import setuptools
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = []

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import sys
        import shlex
        import pytest

        errno = pytest.main(['tests/'] + shlex.split(self.pytest_args or ''))
        sys.exit(errno)


setup_params = dict(
    name='pytestlab',
    version='0.1.0.alpha',
    packages=setuptools.find_packages(),
    install_requires=[
        'SQLAlchemy',
        'cached-property',
        'colorlog',
        'contextlib2',
        'docker',
        'ipaddress',
        'paramiko',
        'plumbum',
        'pyroute2',
        'pytest',
        'python-etcd',
        'pyyaml',
        'rpyc',
        'execnet',
    ],
    extras_require={
        ':python_version < "3.0"': [
            'future'
        ],
    },
    tests_require=['pytest'],
    setup_requires=['setuptools>=17.1'],
    cmdclass={'test': PyTest},
    entry_points={
        'pytest11': [
            'roles=plugins.roles',
            'futurize=plugins.futurize',
            '_storage=plugins.storage',
            'logwatch=plugins.logwatch',
            'log=plugins.log',
            'network=plugins.network',
            'runnerctl=plugins.runnerctl',
            'rpc=plugins.rpc',
            'api=plugins.api',
            'docker=plugins.docker',
            'locker=plugins.locker',
        ]
    }
)

if __name__ == '__main__':
    setuptools.setup(**setup_params)
