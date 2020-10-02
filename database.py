#!/usr/bin/env python

"""
sql.mit.edu database models
"""

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative
from sqlalchemy.sql.expression import text, bindparam
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import ForeignKey, DDLElement
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.compiler import compiles

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
    DatabaseId = sqlalchemy.Column(mysql.INTEGER(10), ForeignKey("DB.DatabaseId"), primary_key=True)
    nBytesSoft = sqlalchemy.Column(mysql.INTEGER(10))
    nBytesHard = sqlalchemy.Column(mysql.INTEGER(10))
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
    DatabaseId = sqlalchemy.Column(mysql.INTEGER(10), ForeignKey("DB.DatabaseId"), primary_key=True)
    UserId = sqlalchemy.Column(mysql.INTEGER(10), ForeignKey("User.UserId"), primary_key=True)
    GroupId = sqlalchemy.Column(mysql.INTEGER(10))

    def __init__(self, user, database):
        self.user = user
        self.database = database
        self.GroupId = 0

    def __repr__(self):
        return "<DBOwner('%d', '%d', '%d')>"  \
            % (self.DatabaseId, self.UserId, self.GroupId)

class Database(Base):
    __tablename__ = 'DB'
    DatabaseId = sqlalchemy.Column(mysql.INTEGER(10), primary_key=True, autoincrement=True)
    Name = sqlalchemy.Column(sqlalchemy.VARCHAR(200), unique=True)
    nBytes = sqlalchemy.Column(mysql.INTEGER(10))
    dLastCheck = sqlalchemy.Column(sqlalchemy.DateTime())
    dCreated = sqlalchemy.Column(sqlalchemy.DateTime())
    bEnabled = sqlalchemy.Column(mysql.INTEGER(3))

    quota = sqlalchemy.orm.relationship(DBQuota, backref=sqlalchemy.orm.backref('database'), cascade='all', uselist=False)
    owner = sqlalchemy.orm.relationship(DBOwner, backref=sqlalchemy.orm.backref('database'), cascade='all', uselist=False)

    def __init__(self, Name):
        self.Name = Name
        self.nBytes = 0
        self.dLastCheck = dt(1900, 1, 1, tzinfo=None)
        self.dCreated = dt.now()
        self.bEnabled = 1

    def __repr__(self):
        return "<Database('%d', '%s', '%d')>"  \
            % (self.DatabaseId, self.Name, self.nBytes)

class UserQuota(Base):
    __tablename__ = 'UserQuota'
    UserId = sqlalchemy.Column(mysql.INTEGER(10), ForeignKey("User.UserId"), primary_key=True)
    nDatabasesHard = sqlalchemy.Column(mysql.INTEGER(10))
    nBytesSoft = sqlalchemy.Column(mysql.INTEGER(10))
    nBytesHard = sqlalchemy.Column(mysql.INTEGER(10))
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
    UserId = sqlalchemy.Column(mysql.INTEGER(10), ForeignKey("User.UserId"), primary_key=True)
    nDatabases = sqlalchemy.Column(mysql.INTEGER(10))
    nBytes = sqlalchemy.Column(mysql.INTEGER(10))
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
    UserId = sqlalchemy.Column(mysql.INTEGER(10), primary_key=True, autoincrement=True)
    Username = sqlalchemy.Column(sqlalchemy.VARCHAR(200), unique=True)
    Password = sqlalchemy.Column(sqlalchemy.VARCHAR(200))
    Name = sqlalchemy.Column(sqlalchemy.Text())
    Email = sqlalchemy.Column(sqlalchemy.Text())
    UL = sqlalchemy.Column(mysql.INTEGER(3))
    dCreated = sqlalchemy.Column(sqlalchemy.DateTime())
    dSignup = sqlalchemy.Column(sqlalchemy.DateTime())
    bEnabled = sqlalchemy.Column(mysql.INTEGER(3))

    quota = sqlalchemy.orm.relationship(UserQuota, backref=sqlalchemy.orm.backref('user'), cascade='all', uselist=False)
    stat = sqlalchemy.orm.relationship(UserStat, backref=sqlalchemy.orm.backref('user'), cascade='all', uselist=False)
    databases = sqlalchemy.orm.relationship(DBOwner, backref=sqlalchemy.orm.backref('user'), cascade='all')

    def __init__(self, Username, Password, Name, Email):
        self.Username = Username
        self.Name = Name
        self.Email = Email
        self.UL = 1
        self.dCreated = dt.now()
        self.dSignup = dt.now()
        self.bEnabled = 1
        self.set_password(Password)
    
    def set_password(self, Password):
        self.Password = base64.b64encode(Password)

    def __repr__(self):
        return "<User('%d','%s')>" % (self.UserId, self.Username)

def formatify(instr):
    """This function is an ugly hack, because something in
    MySQLdb/sqlalchemy goes wrong whenever there's a '%' (wildcard)
    character, and it tries to run it through python's string
    formatter. This is terrible, but it's better than being
    insecure. Deal by escaping the %s."""
    return instr.replace('%', '%%')

class CreateDatabase(DDLElement):
    def __init__(self, name):
        self.name = name

@compiles(CreateDatabase)
def visit_create_database(element, compiler, **kw):
    return formatify("CREATE DATABASE %s" % (compiler.preparer.quote_identifier(element.name),))

class DropDatabase(DDLElement):
    def __init__(self, name, ignore=False):
        self.name = name
        self.ignore = ignore

@compiles(DropDatabase)
def visit_drop_database(element, compiler, **kw):
    if_exists = "IF EXISTS" if element.ignore else ""
    return formatify("DROP DATABASE %s %s" % (if_exists, compiler.preparer.quote_identifier(element.name)))

class CreateUser(DDLElement):
    def __init__(self, name, host, passwd):
        self.name = name
        self.host = host
        self.passwd = passwd

@compiles(CreateUser)
def visit_create_user(element, compiler, **kw):
    return formatify("CREATE USER %s@%s IDENTIFIED BY %s" % \
        tuple([compiler.sql_compiler.render_literal_value(x, sqlalchemy.String) for x in (element.name, element.host, element.passwd)]))

class DropUser(DDLElement):
    def __init__(self, name, host):
        self.name = name
        self.host = host

@compiles(DropUser)
def visit_drop_user(element, compiler, **kw):
    return formatify("DROP USER %s@%s" % \
        tuple([compiler.sql_compiler.render_literal_value(x, sqlalchemy.String) for x in (element.name, element.host)]))

class ChangePassword(DDLElement):
    def __init__(self, name, host, passwd):
        self.name = name
        self.host = host
        self.passwd = passwd

@compiles(ChangePassword)
def visit_change_password(element, compiler, **kw):
    return formatify("SET PASSWORD FOR %s@%s = PASSWORD(%s)" % \
        tuple([compiler.sql_compiler.render_literal_value(x, sqlalchemy.String) for x in (element.name, element.host, element.passwd)]))

class Grant(DDLElement):
    def __init__(self, db, user, host):
        self.db = db
        self.user = user
        self.host = host

@compiles(Grant)
def visit_grant(element, compiler, **kw):
    return formatify("GRANT ALL ON %s.* TO %s@%s" % \
        (compiler.preparer.quote_identifier(element.db),
         compiler.sql_compiler.render_literal_value(element.user, sqlalchemy.String),
         compiler.sql_compiler.render_literal_value(element.host, sqlalchemy.String)))

class Revoke(DDLElement):
    def __init__(self, db, user, host):
        self.db = db
        self.user = user
        self.host = host

@compiles(Revoke)
def visit_revoke(element, compiler, **kw):
    return formatify("REVOKE ALL ON %s.* FROM %s@%s" % \
        (compiler.preparer.quote_identifier(element.db),
         compiler.sql_compiler.render_literal_value(element.user, sqlalchemy.String),
         compiler.sql_compiler.render_literal_value(element.host, sqlalchemy.String)))

