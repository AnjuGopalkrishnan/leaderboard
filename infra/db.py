from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float, MetaData, Table
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

import os
#engine = create_engine('postgresql://postgres:admin@localhost:5432/leaderboard', echo=True)
engine = create_engine(os.environ.get("DB_CONNECTION_URL") + os.environ.get("DATABASE"), echo=True)
metadata = MetaData()
connection = engine.connect()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
db = SessionLocal()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


users = Table(
    'users', metadata,
    Column('user_id', Integer, primary_key=True, index=True),
    Column('email', String, primary_key=True),
    Column('username', String, primary_key=True),
    Column('password', String),
)

competitions = Table(
    'competitions', metadata,
    Column('c_id', Integer, primary_key=True),
    Column('title', String),
    Column('query_type', Integer),
    Column('description', String),
    Column('schema', String),
    Column('solution', String),
    Column('host_user_id', Integer, ForeignKey("users.user_id")),
    Column('metric', Integer),
    Column('due_date', DateTime),
)


class User(Base):
    __table__ = users


class Competitions(Base):
    __table__ = competitions

submissions = Table(
    'submissions', metadata,
    Column('c_id', Integer, ForeignKey("competitions.c_id"), primary_key=True),
    Column('user_id', Integer, ForeignKey("users.user_id"), primary_key=True),
    Column('submission', String),
    Column('timestamp', DateTime, default=datetime.utcnow),
    Column('planning_time', Float),
    Column('execution_time', Float),
    Column('total_time', Float),
    Column('query_complexity', Float),
    Column('attempt_number', Integer, primary_key=True),
)


class Submissions(Base):
    __table__ = submissions


def GetDBConnection():
    return connection
