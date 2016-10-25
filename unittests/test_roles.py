import pytest


@pytest.fixture
def mockctl(testdir):
    testdir.makepyfile(mockctl="""
        import pytest
        import mock
        from lab.ctl import base

        pytest_plugins = 'lab'

        class MyCtl(base.Controller):
            def __init__(self, location, **kwargs):
                super(type(self), self).__init__(location, **kwargs)
                self.setup = mock.MagicMock()
                self.teardown = mock.MagicMock()

        # mocks a role factory definition
        global_mock = mock.Mock(side_effect=MyCtl)

        @pytest.fixture
        def mock_factory():
            return global_mock

        def pytest_lab_addroles(rolemanager):
            rolemanager.register('mock', global_mock)

        @pytest.fixture
        def localhost():
            return pytest.env.manage('localhost')
    """)


def test_manage_location(testdir):
    testdir.makeconftest("""
        pytest_plugins = 'lab'
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


def test_role_loading(mockctl, testdir):
    testdir.makeconftest("""
        pytest_plugins = 'mockctl'

        def pytest_lab_role_created(config, ctl):
            if ctl.name == 'mock':
                ctl.setup()

        def pytest_lab_role_destroyed(config, ctl):
            if ctl.name == 'mock':
                ctl.teardown()
    """)

    testdir.makepyfile("""
        def test_add_role(localhost, mock_factory):
            role = localhost.role('mock', doggy='doggy')

            # test location arg and kwargs pass through on build
            mock_factory.assert_called_once_with(localhost, doggy='doggy')

            assert role.name == 'mock'
            assert role.location == localhost
            role.setup.assert_called_once_with()

            localhost.destroy(role)
            role.teardown.assert_called_once_with()
    """)

    result = testdir.runpytest_subprocess('--env', 'mock')
    assert result.ret == 0


def test_load_unknown_role(mockctl, testdir):
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
        import pytest

        def test_add_role(localhost):
            mock1 = localhost.role('mock')
            assert mock1.name == 'mock'

            localhost.destroy(mock1)
            assert mock1 not in localhost.roles
            # role deletion should also do plugin deregistration
            assert not pytest.env.config.pluginmanager.is_registered(mock1)

            mock2 = localhost.role('mock')
            assert mock2.name == 'mock'
            assert mock1 is not mock2
    """)

    result = testdir.runpytest_subprocess('--env', 'mock')
    assert result.ret == 0
