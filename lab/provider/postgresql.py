import os
import sqlalchemy
import logging
from sqlalchemy import Column, Integer, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound


# FIXME: this shouldn't be hardcoded... yay alpha quality
CONNECTION_STRING = "postgresql://pycopia@sng-qa-db.qa.sangoma.local/pycopia"

db = sqlalchemy.create_engine(CONNECTION_STRING)
engine = db.connect()
Base = declarative_base()
log = logging.getLogger(__name__)


class Record(Base):
    __tablename__ = 'records'
    id = Column(Integer, primary_key=True)
    path = Column(Text)
    doc = Column(JSON)


Base.metadata.create_all(engine)
SessionFactory = sessionmaker(engine)


class PostgresqlProvider(object):
    name = 'postgresql'

    def __init__(self, *path, **kwargs):
        self.session = SessionFactory()

        self.path = os.path.join(*path)
        log.debug("reading from {} with {}".format(
            self.path, type(self).__name__))

        try:
            rows = self.session.query(Record)
            self.row = rows.filter(Record.path == self.path).one()
        except NoResultFound:
            self.row = Record(path=self.path)
            self.session.add(self.row)

    @property
    def data(self):
        return self.row.doc

    def push(self, data):
        self.row.doc = data
        self.session.commit()
