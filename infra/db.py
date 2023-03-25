from sqlalchemy import create_engine, Column, Integer, String, DateTime,BigInteger,ForeignKey,inspect,MetaData,Table
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql://postgres@localhost:5432/leaderboard', echo=True)
metadata = MetaData()
connection = engine.connect()
Base = declarative_base()


competitions = Table(
   'competitions', metadata,
   Column('c_id', BigInteger, primary_key = True),
   Column('description', String),
   Column('schema', String),
   Column('solution', String),
   Column('host_user_id', Integer,primary_key = True),
   Column('due_date', DateTime,primary_key = True),
)

class Competitions(Base):
   __table__ = competitions


submissions = Table(
   'submissions', metadata,
   Column('c_id', Integer, primary_key = True),
   Column('user_id', Integer, primary_key = True),
   Column('submission', String),
   Column('score', Integer),
   Column('timestamp', DateTime,primary_key = True),
)

class Submissions(Base):
   __table__ = submissions

def GetDBConnection():
    return connection
