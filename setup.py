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
import sys
import setuptools
from setuptools.command.test import test as TestCommand


install_requires=[
    'SQLAlchemy',
    'cached-property',
    'colorlog',
    'contextlib2',
    'docker',
    'paramiko',
    'plumbum',
    'pyroute2',
    'pytest',
    'python-etcd',
    'pyyaml',
    'rpyc',
    'ruamel.yaml',
    'execnet',
]

pytest_plugins = [
    'map=pytest_lab.map',
    'roles=pytest_lab.roles',
    '_storage=pytest_lab.storage',
    'logwatch=pytest_lab.logwatch',
    'log=pytest_lab.log',
    'network=pytest_lab.network',
    'runnerctl=pytest_lab.runnerctl',
    'rpc=pytest_lab.rpc',
    'api=pytest_lab.api',
    'docker=pytest_lab.docker',
    'locker=pytest_lab.locker',
    'data=pytest_lab.data',
]


try:
    import ipaddress
except ImportError:
    install_requires.append('ipaddress')


if sys.version_info < (3, 0):
    install_requires.append('future')
    pytest_plugins.append('futurize=pytest_lab.futurize')


setuptools.setup(
    name='pytestlab',
    version='0.1.2.alpha',
    packages=setuptools.find_packages(exclude=('tests',)),
    install_requires=install_requires,
    tests_require=['pytest'],
    entry_points={'pytest11': pytest_plugins}
)
