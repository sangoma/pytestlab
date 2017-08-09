import pytest


@pytest.fixture
def testdir_with_map(testdir):
    testdir.makefile('.yaml', map='''
        version: 1

        environments:
          mock_env:
            roles:
              mock:
                - mocker.example:
                    greeting: Hello World
    ''')

    testdir.makepyfile(mocker='''
        class Greeting:
            def __init__(self, greeting):
                self.greeting = greeting

        def example(greeting):
            return Greeting(greeting)
    ''')

    return testdir


def test_aquire(pytestconfig):
    assert pytest.roles.data['mock']
    assert pytest.roles.data['mock']['mocker.example']


def test_aquire(testdir_with_map):
    testdir_with_map.makepyfile('''
        import pytest

        def test_read_environment(request):
            mock = pytest.roles.aquire('mock')
            assert mock.name == 'mock'
            assert mock.greeting == 'Hello World'
    ''')

    result = testdir_with_map.runpytest('--env=mock_env')
    assert result.ret == 0
