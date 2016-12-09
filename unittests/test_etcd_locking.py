"""
Test inter-session locking via etcd
"""
import signal
import time
import inspect
import pytest
import lab


@pytest.fixture
def dut_loc():
    """Access the `dut` role's location implicitly locking it.
    """
    loc = pytest.env.get_locations('dut')[0]
    assert loc in pytest.env
    assert loc.hostname in pytest.env.locations
    yield loc
    if loc in pytest.env:
        pytest.env.destroy(loc)
    assert loc.hostname not in pytest.env.locations
    assert not loc.envmng.locker.is_locked(loc.hostname)


def test_fail_on_multiple_acquires(discovery_srv, dut_loc):
    """Verify that multiple acquires for the same resource name raises an
    error.
    """
    loc = dut_loc
    assert pytest.env.locker.is_locked(loc.hostname)
    assert loc

    # locations should be cached - shouldn't trigger ResourceLocker.acquire()
    loc2 = pytest.env.get_locations('dut')[0]
    assert loc is loc2
    loc3 = pytest.env.manage(loc.hostname, loc.facts)
    assert loc3 is loc

    with pytest.raises(lab.lock.TooManyLocks):
        pytest.env.locker.acquire(loc.hostname)

    pytest.env.destroy(loc)  # implicit lock release
    assert not pytest.env.locker.is_locked(loc.hostname)
    pytest.env.get_locations('dut')[0]
    assert pytest.env.locker.is_locked(loc.hostname)


def test_inter_session_locking(testdir, discovery_srv, testplugin, dut_loc):
    """Verify that multiple sessions lock each other out of locations.
    """
    assert dut_loc in pytest.env
    locker = pytest.env.locker
    assert locker
    assert locker.is_locked(dut_loc.hostname)

    testdir.makepyfile("""
        import pytest
        import lab

        def test_lock(pytestconfig, discovery_srv):
            with pytest.raises(lab.lock.ResourceLocked):
                loc = pytest.env.get_locations('dut', timeout=0)[0]
    """)
    testdir.makeconftest(inspect.getsource(testplugin))
    result = testdir.runpytest_subprocess(
        '-s',
        '--discovery-srv={}'.format(discovery_srv),
    )
    assert result.ret == 0, result.stdout.str()

    # swap the lock between sessions
    pytest.env.destroy(dut_loc)
    assert not pytest.env.locker.is_locked(dut_loc.hostname)

    testdir.makepyfile("""
        import pytest
        import lab

        def test_lock(pytestconfig, discovery_srv):
            loc = pytest.env.get_locations('dut', timeout=0)[0]
    """)
    testdir.makeconftest(inspect.getsource(testplugin))
    result = testdir.runpytest_subprocess(
        '-s',
        '--discovery-srv={}'.format(discovery_srv),
    )
    assert result.ret == 0, result.stdout.str()


def poll_for_patt(patt, pexpect):
    lines = []
    line = pexpect.readline()
    while line:
        line = line.strip()
        if line:
            print("pytest-spawn: {}".format(line))
            lines.append(line)
            if patt in line:
                return line
        line = pexpect.readline()
    return ''.join(lines)


def poll_pexpect(pexpect, timeout=3):
    start = time.time()
    while time.time() - start < timeout:
        if not pexpect.isalive():
            break
        time.sleep(0.1)
    else:
        assert not pexpect.isalive()


def test_wait_on_lock(testdir, discovery_srv, testplugin, dut_loc):
    """Verify that a session can unlock a resource for the next waiter.
    """
    locker = pytest.env.locker
    assert locker

    testdir.makeconftest(inspect.getsource(testplugin))
    testdir.makepyfile("""
        import pytest
        import lab

        def test_lock(pytestconfig, discovery_srv):
            loc = pytest.env.get_locations('dut')[0]
    """)
    pexpect = testdir.spawn_pytest(
        '-s --discovery-srv={}'.format(discovery_srv),
    )

    lockid = lab.lock.get_lock_id()
    onscreen = poll_for_patt(lockid, pexpect)
    assert '{} is locked by {}'.format(dut_loc.hostname, lockid) in onscreen

    # ensure ctl-c stops the sess gracefully
    time.sleep(0.5)
    pexpect.kill(signal.SIGINT)
    poll_for_patt('KeyboardInterrupt', pexpect)
    poll_pexpect(pexpect)
    pexpect.close()
    assert pexpect.exitstatus == 2  # SIGINT
    testdir.tmpdir.join('pexpect').remove()

    # this time unlock the parent session and ensure the spawn completes
    pexpect = testdir.spawn_pytest(
        '-s --discovery-srv={}'.format(discovery_srv),
    )
    assert locker.is_locked(dut_loc.hostname)
    onscreen = poll_for_patt(lockid, pexpect)
    assert '{} is locked by {}'.format(dut_loc.hostname, lockid) in onscreen

    pytest.env.destroy(dut_loc)  # releases lock
    onscreen = poll_for_patt("1 passed", pexpect)
    poll_pexpect(pexpect)
    assert pexpect.exitstatus == 0


def test_timeout_on_lock(testdir, discovery_srv, testplugin, dut_loc):
    """Verify that a locked location waiting call will eventually timeout.
    """
    lockid = lab.lock.get_lock_id()
    testdir.makeconftest(inspect.getsource(testplugin))
    testdir.makepyfile("""
        import pytest
        import lab

        def test_lock(pytestconfig, discovery_srv):
            with pytest.raises(lab.lock.ResourceLocked):
                loc = pytest.env.get_locations('dut', timeout=1)[0]
    """)
    testdir.makeconftest(inspect.getsource(testplugin))
    result = testdir.runpytest_subprocess(
        '-s',
        '--discovery-srv={}'.format(discovery_srv),
    )
    assert result.ret == 0
    result.stderr.fnmatch_lines(
        '*{} is locked by {}*'.format(dut_loc.hostname, lockid))
