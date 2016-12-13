import pytest
import ipaddress
from lab import network


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
