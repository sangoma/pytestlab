import six
import collections
import db
import cPickle as pickle
from sqlalchemy import create_engine, sql


__all__ = ['normalize_hostnames', 'normalize_role', 'Importer']


ROLE_NORMALIZATION = {
    'build_server': 'jenkins',
    'call_generator': 'freeswitch',
    'asterisk_slave': 'asterisk'
}


def normalize_hostnames(hostname):
    return HOSTNAME_NORMALIZATION.get(hostname, hostname)


HOSTNAME_NORMALIZATION = {
    'to-hudson.sangoma.local': 'jenkins.eng.sangoma.local'
}


def normalize_role(role):
    return ROLE_NORMALIZATION.get(role, role)


# SQL query to preload a map of testequipment ids to software categories
# (our notion of roles). We'll do this seperately because of the logic
# isn't a simple foreign key constraint, unfortunately.
role_map_query = sql.select([
    db.testequipment_roles.c.testequipment_id,
    db.software_category.c.name
]).select_from(
    db.testequipment_roles.join(
        db.software_category)
)

# Query an environment with all attached equipment. Retrieves the
# environment name, the hostname attribute (we only care about
# hostnames, not the equipment name), and if its either a DUT/UUT or
# some other specific role.
environment_query = sql.select([
    db.environments.c.name,
    db.equipment_attributes.c.value,
    db.testequipment.c.UUT,
    db.testequipment.c.id,
    db.equipment_model.c.name
]).select_from(
    db.environments.join(
        db.testequipment.join(
            db.equipment.join(
                db.equipment_attributes.join(
                    db.attribute_type)
            ).outerjoin(db.equipment_model)))
).where(db.attribute_type.c.name == 'hostname')

# Query the first piece of equipment's primary key from its hostname
# attribute.
equipment_find_query = sql.select([
    db.equipment.c.id,
]).select_from(
    db.equipment.join(
        db.equipment_attributes.join(
            db.attribute_type))
).where(sql.and_(
    db.attribute_type.c.name == 'hostname',
    db.equipment_attributes.c.value == sql.bindparam('equipname')
)).as_scalar()

# Query for all the attributes (ignoring the hostname attribute) for an
# equipment specified by its hostname.
equipment_query = sql.select([
    db.attribute_type.c.name,
    db.equipment_attributes.c.value,
]).select_from(
    db.equipment.join(
        db.equipment_attributes.join(
            db.attribute_type))
).where(sql.and_(
    db.equipment.c.id == equipment_find_query,
    db.attribute_type.c.name != 'hostname',
    db.attribute_type.c.name != 'accessmethod')
)


class Importer(object):
    def __init__(self, *args, **kwargs):
        self.engine = create_engine(*args, **kwargs)
        self.conn = self.engine.connect()

        # Prefetch the equipment id to software category (role) name map
        self.roleids = dict(self.conn.execute(role_map_query).fetchall())

    def environments(self, envname=None):
        query = environment_query
        if envname:
            query = query.where(db.environments.c.name == envname)

        envs = collections.defaultdict(dict)
        results = self.conn.execute(query, envname=envname)

        for env, equip, is_dut, type_id, model in results:
            role = model.lower() if is_dut else self.roleids[type_id]
            equip = pickle.loads(six.binary_type(equip))
            envs[env][role] = equip

        return dict(envs)

    def equipment(self, equipname):
        equipname = six.binary_type(equipname)
        results = self.conn.execute(equipment_query,
                                    equipname=pickle.dumps(equipname))
        return {key: pickle.loads(six.binary_type(value))
                for key, value in results.fetchall()}
