import re
import random

from sqlalchemy import create_engine
from sqlalchemy import MetaData, Table, Column, String, Integer, Float
from sqlalchemy.sql import select, text
from sqlalchemy.engine.reflection import Inspector

def connect(db_config):
    stores = [Store(connect_string) for connect_string in db_config]
    return DistStore(stores)
    
class DistStore(object):
    """
    Distributed Data Store
    """
    DIST_TYPE_ANY = 0
    DIST_TYPE_ALL = 1
    DIST_TYPE_PRIMARY = 2

    def __init__(self, stores):
        self.stores = stores

    def select(self, table, where, dist_type=DIST_TYPE_ALL):
        stores = self._select_store(dist_type)
        return sum([s.select(table, where) for s in stores], [])

    def insert(self, table, row, dist_type=DIST_TYPE_ANY):
        return self.bulk_insert(table, [row], dist_type)

    def bulk_insert(self, table, rows, dist_type=DIST_TYPE_ANY):
        stores = self._select_store(dist_type)
        [s.bulk_insert(table, rows) for s in stores]

    def create_table(self, name, columns, dist_type=DIST_TYPE_ALL):
        stores = self._select_store(dist_type)
        [s.create_table(name, columns) for s in stores]

    def table_exists(self, name, dist_type=DIST_TYPE_ALL):
        stores = self._select_store(dist_type)
        return all(s.table_exists(name) for s in stores)

    def _select_store(self, dist_type):
        if dist_type == self.DIST_TYPE_ALL:
            return self.stores
        elif dist_type == self.DIST_TYPE_ANY:
            return [random.choice(self.stores)]
        elif dist_type == self.DIST_TYPE_PRIMARY:
            return [self.stores[0]]

class Store(object):
    DEFAULT_DRIVERS = {
        'mysql': 'pymysql',
    }

    def __init__(self, connect_string):
        self.engine = self._create_engine(connect_string)
        self.metadata = MetaData(self.engine)
        inspector = Inspector.from_engine(self.engine)
        self.table_names = set(inspector.get_table_names())
        self.tables = {}

    def _create_engine(self, connect_string):
        for db_type, driver in self.DEFAULT_DRIVERS.iteritems():
            connect_string = connect_string.replace(
                db_type + '://', 
                '{}+{}://'.format(db_type, driver)
            )
        return create_engine(connect_string, echo=True)

    def _get_table(self, name):
        if not name in self.tables:
            self.tables[name] = Table(name, self.metadata, autoload=True) 
        return self.tables[name]

    def _type_mapping(self, type_name):
        """
        Convert a column type name to a SQLAlchemy Type object
        """
        if type_name == 'float':
            return Float
        elif type_name == 'int':
            return Integer
        elif type_name.startswith('string'):
            str_length = type_name.replace('string','').strip('()')
            return String(str_length) if str_length.isdigit() else String

    def select(self, table_name, where):
        where_clause = ' and '.join([(col + '= :' + col) for col in where.iterkeys()])
        s = text("select * from {} where {}".format(table_name, where_clause) )
        conn = self.engine.connect()
        return conn.execute(s, **where).fetchall()

    def bulk_insert(self, table_name, rows):
        conn = self.engine.connect()
        table = self._get_table(table_name)
        return conn.execute(table.insert(), rows)

    def create_table(self, name, columns):
        columns = [
            Column(c['name'], self._type_mapping(c['type']), primary_key=c.get('primary_key', False))
            for c in columns
        ]
        table = Table(name, self.metadata, *columns)
        table.create()
        self.table_names.add(table)
        return table

    def table_exists(self, table_name):
        return table_name in self.table_names
