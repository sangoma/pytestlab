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
],


try:
    import ipaddress
except ImportError:
    install_requires.append('ipaddress')


setup_params = dict(
    name='pytestlab',
    version='0.1.0.alpha',
    packages=setuptools.find_packages(),
    install_requires=install_requires,
    extras_require={
        ':python_version < "3.0"': [
            'future'
        ],
    },
    tests_require=['pytest'],
    entry_points={
        'pytest11': [
            'map=pytest_lab.map',
            'roles=pytest_lab.roles',
            'futurize=pytest_lab.futurize',
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
    }
)

if __name__ == '__main__':
    setuptools.setup(**setup_params)
