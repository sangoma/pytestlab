"""
High level networking helpers
"""
import pytest
import socket
import contextlib2
from .. import network


def calculate_addr_family(config):
    addr_family = []
    has_ipv4 = has_ipv6 = False

    try:
        dut = pytest.env.find_one('nsc')
    except pytest.EquipmentLookupError:
        pytest.log.warn(
            "All DUTs other then NSC are currently restricted to ipv4"
        )
        has_ipv4 = True
    else:
        addrinfo = dut.addrinfo  # DNS lookup
        has_ipv4 = socket.AF_INET in addrinfo
        has_ipv6 = socket.AF_INET6 in addrinfo
        if not has_ipv6:
            pytest.log.warn(
                "ipv6 tests will not be generated due to DNS lookup failure"
            )

    # Precompute the all parameterization values, identifiers, and
    # marks. If we do this at generate test time, the number of DNS
    # requests done seriously bogs down the collection times. The mark
    # here is meant to be the mark to exclude particular tests from
    # being generated, even it they otherwise would be.
    if pytest.options.get('ipv4', has_ipv4):
        addr_family.append((socket.AF_INET, 'v4', 'noipv4'))
    if pytest.options.get('ipv6', has_ipv6):
        addr_family.append((socket.AF_INET6, 'v6', 'noipv6'))
    return addr_family


def pytest_generate_tests(metafunc):
    """Parametrize tests for both ipv 4 and 6.
    Only use ipv6 if a sucessful DNS query is made.
    """
    if 'addr_family' not in metafunc.fixturenames:
        return

    def effective_addr_family(addr_family):
        for param, id, exclusion_mark in addr_family:
            if not hasattr(metafunc.function, exclusion_mark):
                yield param, id

    config = metafunc.config

    if not config.addr_family:
        # should be called only once to avoid repeat DNS queries
        config.addr_family = calculate_addr_family(config)

    addr_family = list(effective_addr_family(config.addr_family))
    if addr_family:
        params, ids = zip(*addr_family)

        metafunc.parametrize('addr_family', params, ids=ids,
                             indirect=True, scope='session')
    else:
        # sometimes there may be no parametrizations supported
        # (eg. tests might run with ipv6 only but the DUT has no
        # ipv6 support configured)
        f = metafunc.function
        pytest.log.warn(
            "{} from {} does not support any of {}".format(
                f, f.__module__, ', '.join(
                    family[1] for family in config.addr_family)
            )
        )


def pytest_runtest_setup(item):
    # Hack to support the noipv6 fixture. FIXME: this should end up in
    # a better place as a more general system.
    # The problem here is that the 'addr_family' fixture is session
    # level, but the mark is at the function level.
    if item.get_marker('noipv6'):
        addr_family = item._request.getfixturevalue('addr_family')
        if addr_family == socket.AF_INET6:
            pytest.skip("Test not enabled for IPv6")

    if item.get_marker('noipv4'):
        addr_family = item._request.getfixturevalue('addr_family')
        if addr_family == socket.AF_INET:
            pytest.skip("Test not enabled for IPv4")


@pytest.fixture(scope='session')
def best_route(dut_host, ip_ver):
    return network.find_best_route(dut_host, version=ip_ver)


@pytest.fixture(scope='session')
def primary_iface(best_route):
    'return the local net iface with the best route to the dut'
    return best_route[0]


@pytest.fixture(scope='session')
def src_ip(best_route):
    'return the local net iface with the best route to the dut'
    return best_route[1].compressed


@pytest.fixture(scope='session')
def addr_family(request, dut_ctl):
    '''The address family to determine the mode - ipv4 or ipv6 - to run
    tests under'''
    if request.param == socket.AF_INET6:
        if socket.AF_INET6 not in dut_ctl.addrinfo:
            pytest.fail("IPv6 mode not supported on DUT")
        elif not next(network.ip_ifaces(version=6), None):
            pytest.fail("No IPv6 interfaces configured")

    return request.param


@pytest.fixture(scope='session')
def ip_ver(addr_family):
    '''Convenience for functions that need 4 or 6'''
    if addr_family == socket.AF_INET:
        return 4
    else:
        return 6


@pytest.fixture(scope='session')
def srv(request):
    '''Lookup the location of a resource through dns SRV records.'''
    import srvlookup
    domain = request.config.getoption('--discovery-srv')

    def lookup(service):
        record = srvlookup.lookup(service, domain=domain)[0]
        return (record.host, record.port)
    return lookup


@pytest.fixture(scope='class')
def vlan(primary_iface):
    '''Create a macvlan device'''
    with network.MacVLan(primary_iface) as vlan:
        yield vlan


@pytest.fixture
def vlan_set(primary_iface):
    "constructor to create a variable set of macvlan interfaces"

    with contextlib2.ExitStack() as stack:
        def inner(count):
            return [stack.enter_context(network.MacVLan(primary_iface))
                    for _ in range(count)]

        yield inner


@pytest.fixture(scope='class')
def vlan_addr(vlan, addr_family):
    '''Return the correct ip address for the macvlan interface'''
    return vlan.get_address(addr_family).compressed
