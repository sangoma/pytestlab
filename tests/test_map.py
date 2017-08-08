import pytest
from lab import config_v1


@pytest.fixture
def testdir_with_map(testdir):
    testdir.makefile('.yaml', map='''
        version: 1

        zones:
          mock_zone:
            roles:
              mock:
                - mocker.example:
                    greeting: Hello Zone

        environments:
          mock_env:
            roles:
              mock:
                - mocker.example:
                    greeting: Hello World

          mock_with_zone:
            zones: [mock_zone]
    ''')

    return testdir


def test_read_environment_map(testdir_with_map):
    testdir_with_map.makepyfile('''
        import pytest

        def test_read_environment(request):
            assert pytest.roles.data['mock']
            assert pytest.roles.data['mock']['mocker.example']
    ''')

    result = testdir_with_map.runpytest('--env=mock_env')
    assert result.ret == 0


def test_read_environment_map_empty(testdir_with_map):
    testdir_with_map.makepyfile('''
        import pytest

        def test_read_environment(request):
            assert pytest.roles.data == {}
    ''')

    result = testdir_with_map.runpytest('--env=mock_env_other')
    assert result.ret == 0


def test_read_environment_with_zone(testdir_with_map):
    testdir_with_map.makepyfile('''
        import pytest

        def test_read_environment(request):
            assert pytest.roles.data['mock']
            assert pytest.roles.data['mock']['mocker.example']
    ''')

    result = testdir_with_map.runpytest('--env=mock_with_zone')
    assert result.ret == 0


def test_read_environment_override_zone(testdir_with_map):
    testdir_with_map.makepyfile('''
        import pytest

        def test_read_environment(request):
            assert pytest.roles.data['mock']
            assert pytest.roles.data['mock']['mocker.example']
    ''')

    result = testdir_with_map.runpytest('--zone=mock_zone')
    assert result.ret == 0


@pytest.fixture
def testdir_with_map_hookimpl(testdir):
    testdir.makeconftest('''
        import pytest

        @pytest.hookimpl
        def pytest_lab_map(config, roles):
            roles.load({'mock': {
                'mocker.example': {'greeting': 'Hello Custom'}
            }}, {})
    ''')

    return testdir


def test_load_custom_map(testdir_with_map_hookimpl):
    testdir_with_map_hookimpl.makepyfile('''
        import pytest

        def test_read_environment(request):
            assert pytest.roles.data['mock']
            assert pytest.roles.data['mock']['mocker.example']
    ''')

    result = testdir_with_map_hookimpl.runpytest()
    assert result.ret == 0
