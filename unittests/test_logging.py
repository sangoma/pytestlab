pytest_plugins = "logwatch"


def test_logwatch_source(testdir):
    testdir.makeconftest("""
        import mock
        import pytest

        pytest_plugins = 'logwatch'

        mocksource = mock.Mock()
        mocksource.capture = mock.Mock(
            return_value=[('test_logwatch.txt', 'Error: This is a test error.')]
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
