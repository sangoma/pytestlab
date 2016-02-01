from setuptools import setup
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
        #import here, cause outside the eggs aren't loaded
        import sys
        import shlex
        import pytest

        errno = pytest.main(['tests/'] + shlex.split(self.pytest_args or ''))
        sys.exit(errno)


setup(name='lab',
      version='0.0.0',
      packages=['lab',
                'lab.provider',
                'lab.pycopia'],
      install_requires=[
          'six',
          'click',
          'pyxdg',
          'python-etcd',
          'srvlookup',
          'ipaddress',
          'pyroute2',
          'sqlalchemy'
      ],
      tests_require=['pytest'],
      cmdclass={'test': PyTest},
      entry_points={
          'console_scripts': ['labctl=lab.client:cli',
                              'labagent=lab.agent:cli']
      }
)
