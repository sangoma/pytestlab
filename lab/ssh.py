'''
Paramiko machine ctl
'''
import os
import types
import logging
import plumbum
from stat import S_ISDIR
from plumbum import ProcessExecutionError
from paramiko import SSHException
from paramiko.agent import Agent as SSHAgent
from paramiko.ssh_exception import AuthenticationException


log = logging.getLogger(__name__)

# Rexport plumbum errors
SSHCommsError = plumbum.machines.session.SSHCommsError
ProcessExecutionError = plumbum.ProcessExecutionError

SSH_OPTS = ['-o', 'UserKnownHostsFile=/dev/null',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ServerAliveInterval=5']


def walk(self, remotepath):
    """Taken from https://gist.github.com/johnfink8/2190472

    A stripped down version of os.walk implemented for sftp which
    yields tuples: (path, folders, files)
    """
    path = remotepath
    files = []
    folders = []
    for f in self.listdir_attr(remotepath):
        if S_ISDIR(f.st_mode):
            folders.append(f.filename)
        else:  # non-dir
            files.append(f.filename)
    yield path, folders, files
    for folder in folders:
        new_path = os.path.join(remotepath, folder)
        for x in self.walk(new_path):
            yield x


def get_paramiko_sftp(location, **kwargs):
    ssh = get_paramiko_ssh(location, **kwargs)
    return ssh.sftp


def get_paramiko_ssh(location, **kwargs):
    from paramiko import AutoAddPolicy
    from plumbum.machines.paramiko_machine import ParamikoMachine

    password = location.facts.get('password')
    keyfile = location.facts.get('keyfile')
    settings = {'user': location.facts.get('user', 'root'),
                'port': location.facts.get('port', 22),
                'look_for_keys': False,
                'missing_host_policy': AutoAddPolicy(),
                'keep_alive': 60}

    if password:
        settings['password'] = password
    if keyfile:
        settings['keyfile'] = keyfile

    ssh = ParamikoMachine(location.hostname, **settings)
    ssh.sftp.walk = types.MethodType(walk, ssh.sftp)
    return ssh


def get_generic_sftp(location, **kwargs):
    import paramiko

    hostname = location.hostname
    port = location.facts.get('port', 22)
    username = location.facts.get('user', 'root')
    password = location.facts.get('password')
    keyfile = location.facts.get('keyfile')

    def get_transport(**kwargs):
        transport = paramiko.Transport(hostname, port)
        transport.connect(**kwargs)
        return transport

    def get_sftp(transport):
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.walk = types.MethodType(walk, sftp)
        return sftp

    def iter_credentials():
        if keyfile:
            log.info("Offering keyfile {}...".format(keyfile))
            pkey = paramiko.RSAKey.from_private_key_file(keyfile)
            yield {'username': username, 'pkey': pkey}

        if password:
            log.info("Offering password...")
            yield {'username': username, 'password': password}

        if 'SSH_AUTH_SOCK' in os.environ:
            agent = SSHAgent()
            for pkey in agent.get_keys():
                log.info("Offering {} key from agent...".format(pkey.name))
                yield {'username': username, 'pkey': pkey}

    err = None
    transport = None

    log.info("Trying SSH connection to {}...".format(hostname))
    for credentials in iter_credentials():
        err = None
        try:
            transport = get_transport(**credentials)
            break
        except AuthenticationException as _:
            err = _
            log.warning("Authentication failed: {}".format(err))

    if err or not transport:
        raise EnvironmentError('Failed to establish ssh transport')
    return get_sftp(transport)


def get_generic_ssh(location, **kwargs):
    from plumbum import SshMachine

    password = location.facts.get('password')
    keyfile = location.facts.get('keyfile')
    settings = {'user': location.facts.get('user', 'root'),
                'port': location.facts.get('port', 22),
                'ssh_opts': SSH_OPTS,
                'scp_opts': SSH_OPTS}

    if password:
        settings['password'] = location.facts.get('password')

    if keyfile:
        keyfile = os.path.expanduser(keyfile)
        assert os.path.isfile(keyfile), 'No keyfile {} exists?'.format(keyfile)
        log.debug("Attempting to auth ssh with keyfile {}".format(keyfile))
        settings['keyfile'] = keyfile
    elif password:
        settings['password'] = location.facts.get('password')

    ssh = SshMachine(location.hostname, **settings)
    return ssh


if os.environ.get('PLUMBUM_BACKEND') == 'paramiko':
    get_ssh = get_paramiko_ssh
    get_sftp = get_paramiko_sftp
else:
    get_ssh = get_generic_ssh
    get_sftp = get_generic_sftp
