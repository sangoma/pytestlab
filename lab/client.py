import io
import sys
import click
import logging
import os

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
@click.option('--targets', '-t', metavar='TARGETS[,...]',
              help='The data providers to query, comma seperated')
@click.option('--loglevel', '-l', metavar='LEVEL',
              help='Explicitly set the python logging level')
@click.option('-v', '--verbose', count=True,
              help='Verbosity level. Pass more then once to increase the '
                   ' logging level')
@click.pass_context
def cli(ctx, discovery_srv, targets, loglevel, verbose):
    # pager options
    os.environ['LESS'] = 'FRSX'
    # explicit level always overrides
    logging.basicConfig(
        level=loglevel.upper() if loglevel else max(40 - verbose * 10, 10)
    )
    ctx.obj = Client(targets, domain=discovery_srv)


@cli.group(help='Manipulate information on lab equipment')
@click.argument('name')
@click.pass_context
def equipment(ctx, name):
    ctx.name = name


@equipment.command('get')
@click.option('--verbose', '-v', is_flag=True)
@pass_client
@click.pass_context
def equipment_get(ctx, client, verbose):
    entry = client.equipment(ctx.parent.name)

    if not entry:
        return
    client.print_entry(entry, verbose)


@equipment.command('set')
@click.argument('key')
@click.argument('value')
@pass_client
@click.pass_context
def equipment_set(ctx, client, key, value):
    entry = client.equipment(ctx.parent.name)

    entry[key] = value
    client.print_entry(entry, True)


@equipment.command('rm')
@click.argument('key', required=False)
@pass_client
@click.pass_context
def equipment_rm(ctx, client, key):
    entry = client.equipment(ctx.parent.name)

    if key and key in entry:
        del entry[key]
        client.print_entry(entry, True)
    else:
        entry.clear()


@cli.group(help='Manipulate and define lab environments')
@click.argument('name')
@click.pass_context
def env(ctx, name):
    ctx.name = name


@env.command('get')
@click.option('--verbose', '-v', is_flag=True)
@pass_client
@click.pass_context
def env_get(ctx, client, verbose):
    entry = client.environment(ctx.parent.name)

    if not entry:
        return
    client.print_entry(entry, verbose)


@env.command('register')
@click.argument('role')
@click.argument('eq')
@pass_client
@click.pass_context
def env_register(ctx, client, role, eq):
    entry = client.environment(ctx.parent.name)

    entry.register(role, eq)
    client.print_entry(entry, True)


@env.command('unregister')
@click.argument('role')
@click.argument('eq', required=False)
@pass_client
@click.pass_context
def env_unregister(ctx, client, role, eq):
    entry = client.environment(ctx.parent.name)

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

    import pycopia

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
