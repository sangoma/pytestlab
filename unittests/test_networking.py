import gc
import socket
import itertools
import contextlib2
import pytest
import ipaddress
from lab import network


@pytest.fixture
def dhcp_network():
    """The default Docker network"""
    return ipaddress.IPv4Network(u'172.17.0.0/16')


@pytest.fixture
def dhcp_range(dhcp_network):
    """A subnet inside the Docker network suitable for use with DHCP"""
    subnets = dhcp_network.subnets(new_prefix=24)
    # Pick the 200th subnet to avoid collisions with Docker's own IP
    # handouts. Shouldn't expect a collision without allocating about
    # 51000 containers.
    return next(itertools.islice(subnets, 200, None))


@pytest.fixture
def dhcpd_config(dhcp_network, dhcp_range, tmpdir):
    """Configuration for dhcpd4 daemon"""
    hosts = list(dhcp_range.hosts())

    tmpdir.join('dhcpd.conf').write('''authoritative;
default-lease-time 600;
max-lease-time 7200;

subnet {network.network_address} netmask {network.netmask} {{
    range {min_host} {max_host};
    option routers {router};
}}
'''.format(network=dhcp_network,
           router=next(dhcp_network.hosts()),
           min_host=hosts[0],
           max_host=hosts[-1]))

    return str(tmpdir)


@pytest.fixture
def dhcpd4(docker, dhcpd_config):
    """Launch dhcpd4 inside a docker container"""
    with docker.image('networkboot/dhcpd', ['eth0'],
                      volumes={dhcpd_config: {'bind': '/data', 'mode': 'rw'}},
                      networks=['host']):
        yield


@pytest.fixture
def macvlan(dhcpd4):
    """Generate for macvlans attached to docker0 interface, with
    automatic cleanup"""
    with contextlib2.ExitStack() as stack:
        yield lambda **kw: stack.enter_context(network.MacVLan('docker0', **kw))

    # Make sure __del__ on the macvlan gets triggered
    gc.collect()


@pytest.mark.parametrize('ip', [
    '127.0.0.1',
    '::1'
])
def test_ping(ip):
    network.ping(ip)


@pytest.mark.parametrize('ip, expected', [
    ('127.0.0.1', 4),
    ('::1', 6)
])
def test_addr_version_detection(ip, expected):
    assert network.get_addr_version(ip) == expected


@pytest.mark.parametrize('ip, version, expected', [
    ('127.0.0.1', 4, ipaddress.IPv4Address(u'127.0.0.1')),
    ('::1', 6, ipaddress.IPv6Address(u'::1')),
    ('localhost.localdomain', 4, ipaddress.IPv4Address(u'127.0.0.1'))
])
def test_check_ipaddr(ip, version, expected):
    assert network.check_ipaddr(ip, version=version) == (expected, ip)


@pytest.mark.parametrize('destination, version, expected', [
    ('localhost', 4, 'lo'),
])
def test_find_best_route(destination, version, expected):
    iface, addr = network.find_best_route(destination, version=version)
    assert iface == expected
    assert addr.version == version


def test_macvlan(dhcpd4, dhcp_range, macvlan):
    vlan = macvlan()
    addresses = vlan.addresses
    assert len(addresses) == 1

    ipv4_addresses = addresses[socket.AF_INET]
    assert len(ipv4_addresses) == 1
    assert ipv4_addresses[0] in dhcp_range
