import pytest


@pytest.fixture
def mockctl(testdir):
    testdir.makepyfile(mockctl="""
        import pytest
        import mock
        pytest_plugins = 'sangoma.lab.roles'

        def pytest_lab_addroles(rolemanager):
            rolemanager.register('mock', mock.Mock())

        @pytest.fixture
        def localhost():
            return pytest.env.manage('localhost')
    """)


def test_manage_location(testdir):
    testdir.makeconftest("""
        pytest_plugins = 'sangoma.lab.roles'
    """)

    testdir.makepyfile("""
        import pytest

        FACTS = {'testing': True}

        def test_manage():
            localhost = pytest.env.manage('localhost', facts=FACTS)
            assert localhost.hostname == 'localhost'
            assert localhost.facts == FACTS
    """)

    # Needs a subprocess because of plumbums's atexit hooks
    result = testdir.runpytest_subprocess('--env', 'mock')
    assert result.ret == 0


def test_register_role(mockctl, testdir):
    testdir.makeconftest("""
        pytest_plugins = 'mockctl'

        def pytest_lab_register_role(config, ctl):
            if ctl.name == 'mock':
                ctl.setup()

        def pytest_lab_delete_role(config, ctl):
            if ctl.name == 'mock':
                ctl.teardown()
    """)

    testdir.makepyfile("""
        def test_add_role(localhost):
            role = localhost.role('mock')
            assert role.name == 'mock'
            role.setup.assert_called_once_with()

            localhost.destroy(role)
            role.teardown.assert_called_once_with()
    """)

    result = testdir.runpytest_subprocess('--env', 'mock')
    assert result.ret == 0


def test_register_unknown_role(mockctl, testdir):
    testdir.makeconftest("""
        pytest_plugins = 'mockctl'
    """)

    testdir.makepyfile("""
        import pytest

        def test_add_role(localhost):
            with pytest.raises(KeyError):
                localhost.role('tyler')
    """)

    result = testdir.runpytest_subprocess('--env', 'mock')
    assert result.ret == 0


def test_request_role_twice(mockctl, testdir):
    testdir.makeconftest("""
        pytest_plugins = 'mockctl'
    """)

    testdir.makepyfile("""
        def test_add_role(localhost):
            mock1 = localhost.role('mock')
            assert mock1.name == 'mock'

            mock2 = localhost.role('mock')
            assert mock2.name == 'mock'
            assert mock1 == mock2
    """)

    result = testdir.runpytest_subprocess('--env', 'mock')
    assert result.ret == 0


def test_register_after_deletion(mockctl, testdir):
    testdir.makeconftest("""
        pytest_plugins = 'mockctl'
    """)

    testdir.makepyfile("""
        def test_add_role(localhost):
            mock1 = localhost.role('mock')
            assert mock1.name == 'mock'

            localhost.destroy(mock1)

            mock2 = localhost.role('mock')
            assert mock2.name == 'mock'
            assert mock1 != mock2
    """)

    result = testdir.runpytest_subprocess('--env', 'mock')
    assert result.ret == 0
