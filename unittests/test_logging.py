import pytest


pytest_plugins = ("lab.logwatch", "pytester")


def test_logwatch_source(testdir):
    testdir.makeconftest("""
        import mock
        import pytest

        pytest_plugins = 'lab.logwatch'

        mocksource = mock.Mock()
        mocksource.capture = mock.Mock(
            return_value=[
                ('test_logwatch.txt', 'Error: This is a test error.')]
        )

        @pytest.hookimpl
        def pytest_lab_log_watch(logmanager):
            logmanager.register(mocksource)
            mocksource.prepare.assert_called_once_with()
            mocksource.prepare.reset_mock()

        @pytest.hookimpl
        def pytest_lab_process_logs(config, item, logs):
            mocksource.prepare.assert_called_once_with()
            mocksource.capture.assert_called_once_with()

            assert item.name == 'test_example'
            assert len(logs) == 1
            assert mocksource.ctl in logs.keys()

            mocklogs = logs[mocksource.ctl]
            assert len(mocklogs) == 1
            assert mocklogs == {
                'test_logwatch.txt': 'Error: This is a test error.'
            }
    """)

    testdir.makepyfile("""
        def test_example():
            pass
    """)

    result = testdir.runpytest()
    assert result.ret == 0


def test_reliable_ssh(testdir, alpine_ssh):
    """Verify that even if all ``logfiles`` ssh connections are closed new
    ones we can still reliably capture logs by creating new connections.
    """
    addr, port = alpine_ssh
    src = """
        import pytest
        from lab.ctl import base
        from sangoma.ssh import get_ssh
        from lab.logwatch import logfiles

        pytest_plugins = ('lab.logwatch', 'lab')

        class Ctl(base.Controller):
            logwatched = False

            def pytest_lab_log_watch(self, logmanager):
                # register for a fake log that shouldn't exist
                logmanager.register(logfiles(self, ('/tmp/', ['fakelog.log'])))
                self.logwatched = True

            @property
            def ssh(self):
                return get_ssh(self.location)


        def pytest_lab_addroles(config, rolemanager):
            rolemanager.register('ctl', Ctl)
            assert not Ctl.logwatched

        @pytest.fixture
        def localhost():
            return pytest.env.manage('localhost', facts={
                'port': 2222, 'password': 'root'})

    """
    testdir.makeconftest(src)
    testdir.makepyfile("""
        import pytest

        def test_ssh_reliability(localhost):
            ctl = localhost.role('ctl')
            assert ctl.logwatched
            lm = pytest.logmanager
            for sourcetypes in lm.sources.values():
                for source in sourcetypes:
                    # purposely close ssh connection
                    source.ssh.close()
    """)

    result = testdir.runpytest_inprocess('--env', 'mock')
    assert result.ret == 0
