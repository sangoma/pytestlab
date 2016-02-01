from sqlalchemy import Table, Column, ForeignKey, MetaData
from sqlalchemy import Integer, String, Boolean, DateTime


metadata = MetaData()

environments = Table('environments', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('owner_id', Integer),
    schema='public')

testequipment = Table('testequipment', metadata,
    Column('id', Integer, primary_key=True),
    Column('equipment_id', Integer, ForeignKey('public.equipment.id')),
    Column('environment_id', Integer, ForeignKey('public.environments.id')),
    Column('UUT', Boolean),
    schema='public')

equipment = Table('equipment', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('model_id', Integer, ForeignKey('public.equipment_model.id')),
    Column('serno', String),
    Column('location_id', Integer),
    Column('sublocation', String),
    Column('addeddate', DateTime(timezone=True)),
    Column('comments', String),
    Column('language_id', Integer),
    Column('owner_id', Integer),
    Column('vendor_id', Integer),
    Column('account_id', Integer),
    Column('parent_id', Integer),
    Column('active', Boolean),
    schema='public')

testequipment_roles = Table('testequipment_roles', metadata,
    Column('id', Integer, primary_key=True),
    Column('testequipment_id', Integer, ForeignKey('public.testequipment.id')),
    Column('softwarecategory_id', Integer, ForeignKey('public.software_category.id')),
    schema='public')

software_category = Table('software_category', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('description', String),
    schema='public')

attribute_type = Table('attribute_type', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('description', String),
    Column('value_type', Integer),
    schema='public')

equipment_attributes = Table('equipment_attributes', metadata,
    Column('id', Integer, primary_key=True),
    Column('type_id', Integer, ForeignKey('public.attribute_type.id')),
    Column('value', String),
    Column('equipment_id', Integer, ForeignKey('public.equipment.id')),
    schema='public')

equipment_model = Table('equipment_model', metadata,
    Column('id', Integer, primary_key=True, nullable=False),
    Column('name', String),
    Column('manufacturer_id', Integer),
    Column('category_id', Integer),
    Column('specs', String),
    Column('picture', String),
    Column('note', String),
    schema='public')
