import io
import sys
import click
import logging

import pycopia
from provider import FileProvider, EtcdProvider
from model import Environment, Equipment, pretty_json


PYCOPIA_DB_URL = 'postgresql://pycopia@sng-qa-db.qa.sangoma.local/pycopia'

logger = logging.getLogger(__name__)


class Client(object):
    PROVIDERS = {provider.name: provider
                 for provider in [FileProvider, EtcdProvider]}

    def __init__(self, targets, **kwargs):
        self.kwargs = kwargs

        if not targets or targets.isspace():
            self.providers = [FileProvider]
        else:
            targets_set = iter(x.strip() for x in targets.split(','))
            self.providers = [Client.PROVIDERS[p] for p in targets_set]

    def equipment(self, name):
        return Equipment(name, self.providers, **self.kwargs)

    def environment(self, name):
        return Environment(name, self.providers, **self.kwargs)

    def print_entry(self, entry, verbose):
        report = io.StringIO()
        if verbose:
            for name, data in entry.providers():
                report.write(u'{}:\n'.format(name))
                report.write(pretty_json(data))
                report.write(u'\n')
        else:
            report.write(pretty_json(entry.view))

        click.echo_via_pager(report.getvalue())


pass_client = click.make_pass_decorator(Client)


@click.group()
@click.option('--discovery-srv', envvar='ETCD_DISCOVERY_SRV',
              metavar='DOMAIN', help='The etcd dns discovery domain')
@click.option('--targets', '-t', metavar='TARGETS',
              help='The data providers to query, comma seperated')
@click.pass_context
def cli(ctx, discovery_srv, targets):
    logging.basicConfig()

    ctx.obj = Client(targets, domain=discovery_srv)


@cli.group(help='Manipulate information on lab equipment')
def equipment():
    pass


@equipment.command('get')
@click.argument('env')
@click.option('--verbose', '-v', is_flag=True)
@pass_client
def equipment_get(client, env, verbose):
    entry = client.equipment(env)

    if not entry:
        return
    client.print_entry(entry, verbose)


@equipment.command('set')
@click.argument('env')
@click.argument('key')
@click.argument('value')
@pass_client
def equipment_set(client, env, key, value):
    entry = client.equipment(env)

    entry[key] = value
    client.print_entry(entry, True)


@equipment.command('rm')
@click.argument('env')
@click.argument('key', required=False)
@pass_client
def equipment_rm(client, env, key):
    entry = client.equipment(env)

    if key and key in entry:
        del entry[key]
        client.print_entry(entry, True)
    else:
        entry.clear()


@cli.group(help='Manipulate and define lab environments')
def environment():
    pass


@environment.command('get')
@click.argument('env')
@click.option('--verbose', '-v', is_flag=True)
@pass_client
def environment_get(client, env, verbose):
    entry = client.environment(env)

    if not entry:
        return
    client.print_entry(entry, verbose)


@environment.command('register')
@click.argument('env')
@click.argument('role')
@click.argument('eq')
@pass_client
def environment_register(client, env, role, eq):
    entry = client.environment(env)

    entry.register(role, eq)
    client.print_entry(entry, True)


@environment.command('unregister')
@click.argument('env')
@click.argument('role')
@click.argument('eq', required=False)
@pass_client
def environment_unregister(client, env, role, eq):
    entry = client.environment(env)

    entry.unregister(role, eq)
    client.print_entry(entry, True)


@cli.command('import', help='Import data from external sources')
@click.argument('source')
@click.argument('type')
@click.argument('name')
@pass_client
def import_data(client, source, type, name):
    if source != 'pycopia':
        click.echo('Unsupported importer', file=sys.stderr)
        sys.exit(1)

    db = pycopia.Importer(PYCOPIA_DB_URL)
    if type == 'environment':
        entry = client.environment(name)
        for roles in db.environments(name).itervalues():
            for role, hostname in roles.iteritems():
                entry.register(pycopia.normalize_role(role),
                               pycopia.normalize_hostnames(hostname))
    elif type == 'equipment':
        entry = client.equipment(name)
        for key, value in db.equipment(name).iteritems():
            entry[key] = value

    client.print_entry(entry, True)


if __name__ == '__main__':
    cli()
