#
# Copyright 2017 Sangoma Technologies Inc.
#
# Adapted for our own use from
# https://github.com/paramiko/paramiko/blob/master/demos/forward.py
from future import standard_library
standard_library.install_aliases()
from builtins import object
import select
import logging
import socket
import threading
import socketserver
import plumbum
from . import get_new_sock


logger = logging.getLogger(__name__)


class ForwardServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            chan = self.remote_machine.connect_sock(self.chain_port,
                                                    self.chain_host)
        except Exception as e:
            logger.error('Incoming request to {}:{} failed: '
                         '{}'.format(self.chain_host, self.chain_port, e))
            return

        if chan is None:
            logger.error('Incoming request to {}:{} was rejected by '
                         'the SSH server.'.format(self.chain_host,
                                                  self.chain_port))
            return

        peername = self.request.getpeername()
        logger.info('Connected! Tunnel open {} -> '
                    '{}'.format(peername, (self.chain_host, self.chain_port)))

        while True:
            r, _, _ = select.select([self.request, chan], [], [])
            if self.request in r:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in r:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)

        peername = self.request.getpeername()
        chan.close()
        self.request.close()
        logger.info('Tunnel closed from {}'.format(peername))


class Tunnel(object):
    def __init__(self, server):
        self.server = server

    def __enter__(self):
        return self.server

    def __exit__(self, *exc_info):
        self.server.shutdown()

    def close(self):
        self.server.shutdown()


def forward_tunnel(ssh, local_port, remote_host, remote_port):
    # This requires a ParamikoMachine. Use SshMachine tunnel support for
    # compatability, but it lacks configuring the remote host
    inst = getattr(ssh, 'driver', ssh)  # may be a connection proxy
    if isinstance(inst, plumbum.SshMachine):
        localhosts = ['localhost', '127.0.0.1', '::1']
        assert remote_host in localhosts, 'Minimal support for SshMachine'
        return ssh.tunnel(local_port, remote_port)

    # this is a little convoluted, but lets me configure things for the
    # Handler object. (SocketServer doesn't give Handlers any way to
    # access the outer server normally.)
    class SubHandler(Handler):
        chain_host = remote_host
        chain_port = remote_port
        remote_machine = ssh

    try:
        server = ForwardServer(('', local_port), SubHandler)
    except socket.error:
        logger.error('Failed to create forwarding server '
                     'on port {}'.format(local_port))
        raise

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    return Tunnel(server)


def tunnel_factory(ssh, remotehost, remoteport):
    """Create tunnels using a random local loopback socket.
    """
    # allocated a random port locally
    host, port = get_new_sock('127.0.0.1')
    tunnel = forward_tunnel(ssh, port, remotehost, remoteport)
    logger.info(
        'Established ssh tunnel from local {}:{} to remote {}:{}'
        .format(host, port, remotehost, remoteport)
    )
    return tunnel, '127.0.0.1', port
