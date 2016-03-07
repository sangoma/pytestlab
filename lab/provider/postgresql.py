import os
import sqlalchemy
from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound


Base = declarative_base()


class JSONRecord(Base):
    __tablename__ = 'records'
    id = Column(Integer, primary_key=True)
    path = Column(Text)
    doc = Column(JSON)


class Record(object):
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
        return self.row.doc

    def push(self, data):
        self.row.doc = data
        self.session.commit()


class PostgresqlProvider(object):
    name = 'postgresql'

    def __init__(self, config):
        engine = sqlalchemy.create_engine(config['database']).connect()
        self.session = sessionmaker(engine)()

        Base.metadata.create_all(engine)

    def get(self, *path):
        return Record(self.session, *path)
