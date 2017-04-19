#
# Copyright 2017 Sangoma Technologies Inc.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from builtins import object
import os
import json
import sqlalchemy
from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from .common import pretty_json


Base = declarative_base()


class JSONRecord(Base):
    __tablename__ = 'records'
    id = Column(Integer, primary_key=True)
    path = Column(Text)
    doc = Column(JSON)


class Record(object):
    """A json record.
    """
    def __init__(self, session, *path):
        self.session = session
        self.path = os.path.join(*path)

        try:
            rows = self.session.query(JSONRecord)
            self.row = rows.filter(JSONRecord.path == self.path).one()
        except NoResultFound:
            self.row = JSONRecord(path=self.path)
            self.session.add(self.row)

    @property
    def data(self):
        return json.loads(self.row.doc) if self.row.doc else {}

    def push(self, data):
        self.row.doc = pretty_json(data)
        self.session.commit()


class PostgresqlProvider(object):
    name = 'postgresql'

    def __init__(self, config):
        engine = sqlalchemy.create_engine(config['database']).connect()
        self.session = sessionmaker(engine)()

        Base.metadata.create_all(engine)

    def get(self, *path, **kwargs):
        return Record(self.session, *path)

    def env_names(self):
        records = self.session.query(JSONRecord)
        env_records = records.filter(JSONRecord.path.like("environment%"))
        return [r.path.partition("/")[2] for r in env_records.all()]
