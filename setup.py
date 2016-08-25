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
        'cliff',
        'colorlog',
        'contextlib2',
        'dnspython',
        'enum34',
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
        'python-etcd',
        'python-redmine',
        'pyxdg',
        'pyyaml',
        'rpyc',
        'safepy2',
        'scipy',
        'six',
        'SQLAlchemy',
        'srvlookup',
        'subprocess32',
        'switchy',
        'tftpy',
        'vegapy',
        'bravado',
    ],
    extras_require={
        'build': ['pycparser', 'cffi'],
    },
    tests_require=['pytest'],
    cmdclass={'test': PyTest},
    entry_points={'console_scripts': ['labctl=lab.app.__main__:main'],
                  'labctl': ['show=lab.app.environments:EnvLister',
                             'add=lab.app.environments:EnvRegister',
                             'rm=lab.app.environments:EnvUnregister',
                             'facts=lab.app.facts:FactsLister',
                             'import=lab.app.import:Importer']},
    cffi_modules=["sangoma/trace/pcap_build.py:ffi"]
)

if __name__ == '__main__':
    setuptools.setup(**setup_params)
