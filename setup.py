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
    name='lab',
    version='0.0.0',
    packages=setuptools.find_packages(),
    install_requires=[
        'beautifulsoup4',
        'bs4',
        'cached-property',
        'cliff',
        'colorlog',
        'contextlib2',
        'dnspython',
        'python-ESL',
        'ipaddress',
        'jenkinsapi',
        'jinja2',
        'libarchive',
        'libvirt-python',
        'lxml',
        'matplotlib',
        'numpy',
        'pandas',
        'paramiko',
        'plumbum',
        'psycopg2',
        'pymongo',
        'pymysql',
        'pyroute2',
        'pysipp',
        'pytest',
        'pytest-instafail',
        'pytest-interactive',
        'pytest-ordering',
        'pytest-pcap',
        'pytest-redmine',
        'python-etcd',
        'pyxdg',
        'pyyaml',
        'rpyc',
        'safepy2',
        'scipy',
        'six',
        'SQLAlchemy',
        'srvlookup',
        'switchy',
        'tftpy',
        'vegapy',
        'bravado',
    ],
    extras_require={
        ':python_version < "3.0"': [
            'future'
        ],
        ':python_version < "3.2"': [
            'subprocess32'
        ],
        ':python_version < "3.4"': [
            'enum34'
        ]
    },
    tests_require=['pytest', 'docker-py'],
    setup_requires=['setuptools>=17.1'],
    cmdclass={'test': PyTest},
    entry_points={
        'console_scripts': ['labctl=lab.app.__main__:main'],
        'labctl': [
            'show=lab.app.environments:EnvLister',
            'add=lab.app.environments:EnvRegister',
            'rm=lab.app.environments:EnvUnregister',
            'facts=lab.app.facts:FactsLister',
        ],
        'pytest11': [
            '_storage=lab.storage'
        ]
    }
)

if __name__ == '__main__':
    setuptools.setup(**setup_params)
