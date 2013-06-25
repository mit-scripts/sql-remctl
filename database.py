#!/usr/bin/env python

"""
sql.mit.edu database models
"""

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative
from sqlalchemy.schema import ForeignKey
from sqlalchemy.engine.url import URL

from datetime import datetime as dt
import base64

_engine = sqlalchemy.create_engine(
    URL(drivername='mysql', host='localhost',
    database='mitsql',
    query={'read_default_file': '/root/.my.cnf'}))

_session = sqlalchemy.orm.sessionmaker(bind=_engine)

Base = sqlalchemy.ext.declarative.declarative_base()

def get_session():
    return _session()

class DBQuota(Base):
    __tablename__ = 'DBQuota'
    DatabaseId = sqlalchemy.Column(sqlalchemy.Integer(10), ForeignKey("DB.DatabaseId"), primary_key=True)
    nBytesSoft = sqlalchemy.Column(sqlalchemy.Integer(10))
    nBytesHard = sqlalchemy.Column(sqlalchemy.Integer(10))
    dCreated = sqlalchemy.Column(sqlalchemy.DateTime())

    def __init__(self, database):
        self.database = database
        self.nBytesSoft = 0
        self.nBytesHard = 0
        self.dCreated = dt.now()

    def __repr__(self):
        return "<DBQuota('%d', '%d', '%d')>"  \
            % (self.DatabaseId, self.nBytesSoft, self.nBytesHard)

class DBOwner(Base):
    __tablename__ = 'DBOwner'
    DatabaseId = sqlalchemy.Column(sqlalchemy.Integer(10), ForeignKey("DB.DatabaseId"), primary_key=True)
    UserId = sqlalchemy.Column(sqlalchemy.Integer(10), ForeignKey("User.UserId"), primary_key=True)
    GroupId = sqlalchemy.Column(sqlalchemy.Integer(10))

    def __init__(self, user, database):
        self.user = user
        self.database = database

    def __repr__(self):
        return "<DBOwner('%d', '%d', '%d')>"  \
            % (self.DatabaseId, self.UserId, self.GroupId)

class DB(Base):
    __tablename__ = 'DB'
    DatabaseId = sqlalchemy.Column(sqlalchemy.Integer(10), primary_key=True, autoincrement=True)
    Name = sqlalchemy.Column(sqlalchemy.VARCHAR(200), unique=True)
    nBytes = sqlalchemy.Column(sqlalchemy.Integer(10))
    dLastCheck = sqlalchemy.Column(sqlalchemy.DateTime())
    dCreated = sqlalchemy.Column(sqlalchemy.DateTime())
    bEnabled = sqlalchemy.Column(sqlalchemy.Integer(3))

    quota = sqlalchemy.orm.relationship(DBQuota, backref=sqlalchemy.orm.backref('database'), cascade='all', uselist=False)
    owner = sqlalchemy.orm.relationship(DBOwner, backref=sqlalchemy.orm.backref('database'), cascade='all', uselist=False)

    def __init__(self, Name):
        self.Name = Name
        self.nBytes = 0
        self.dLastCheck = dt(1900, 1, 1, tzinfo=None)
        self.dCreated = dt.now()
        self.bEnabled = 1

    def __repr__(self):
        return "<DB('%d', '%s', '%d')>"  \
            % (self.DatabaseId, self.Name, self.nBytes)

class UserQuota(Base):
    __tablename__ = 'UserQuota'
    UserId = sqlalchemy.Column(sqlalchemy.Integer(10), ForeignKey("User.UserId"), primary_key=True)
    nDatabasesHard = sqlalchemy.Column(sqlalchemy.Integer(10))
    nBytesSoft = sqlalchemy.Column(sqlalchemy.Integer(10))
    nBytesHard = sqlalchemy.Column(sqlalchemy.Integer(10))
    dCreated = sqlalchemy.Column(sqlalchemy.DateTime())

    def __init__(self, user):
        self.user = user
        self.nDatabasesHard = 20
        self.nBytesSoft = 90 * 1024 * 1024
        self.nBytesHard = 100 * 1024 * 1024
        self.dCreated = dt.now()

    def __repr__(self):
        return "<UserQuota('%d', '%d', '%d', '%d')>"  \
            % (self.UserId, self.nDatabasesHard, self.nBytesSoft, self.nBytesHard)

class UserStat(Base):
    __tablename__ = 'UserStat'
    UserId = sqlalchemy.Column(sqlalchemy.Integer(10), ForeignKey("User.UserId"), primary_key=True)
    nDatabases = sqlalchemy.Column(sqlalchemy.Integer(10))
    nBytes = sqlalchemy.Column(sqlalchemy.Integer(10))
    dLastCheck = sqlalchemy.Column(sqlalchemy.DateTime())

    def __init__(self, user):
        self.user = user
        self.nDatabases = 0
        self.nBytes = 0 
        self.dLastCheck = dt(1900, 1, 1, tzinfo=None)

    def __repr__(self):
        return "<UserStat('%d', '%d', '%d')>"  \
            % (self.UserId, self.nDatabases, self.nBytes)

class User(Base):
    __tablename__ = 'User'
    UserId = sqlalchemy.Column(sqlalchemy.Integer(10), primary_key=True, autoincrement=True)
    Username = sqlalchemy.Column(sqlalchemy.VARCHAR(200), unique=True)
    Password = sqlalchemy.Column(sqlalchemy.VARCHAR(200))
    Name = sqlalchemy.Column(sqlalchemy.Text())
    Email = sqlalchemy.Column(sqlalchemy.Text())
    UL = sqlalchemy.Column(sqlalchemy.Integer(3))
    dCreated = sqlalchemy.Column(sqlalchemy.DateTime())
    dSignup = sqlalchemy.Column(sqlalchemy.DateTime())
    bEnabled = sqlalchemy.Column(sqlalchemy.Integer(3))

    quota = sqlalchemy.orm.relationship(UserQuota, backref=sqlalchemy.orm.backref('user'), cascade='all')
    stat = sqlalchemy.orm.relationship(UserStat, backref=sqlalchemy.orm.backref('user'), cascade='all')
    databases = sqlalchemy.orm.relationship(DBOwner, backref=sqlalchemy.orm.backref('user'), cascade='all')

    def __init__(self, Username, Password, Name, Email):
        self.Username = Username
        self.Password = base64.b64encode(Password)
        self.Name = Name
        self.Email = Email
        self.UL = 1
        self.dCreated = dt.now()
        self.dSignup = dt.now()
        self.bEnabled = 1
    
    def __repr__(self):
        return "<User('%d','%s')>" % (self.UserId, self.Username)
