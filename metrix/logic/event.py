import logging
import time
import yaml
from datetime import datetime

from metrix import const
from metrix.store.base import DistStore

_meta_defaults = {
    'int_columns': 6,
    'float_columns': 3,
    'string_columns': 6,
    'string_max_len': 255,
}

logger = logging.getLogger(__name__)

def _validate_event(evt, schema):
    for prop, val in evt.get('properties', {}).iteritems():
        if prop not in schema:
            return False
        prop_def = schema[prop]
        if prop_def == const.TYPE_INT and not isinstance(val, int):
            return False
        elif prop_def == const.TYPE_FLOAT and not isinstance(val, float):
            return False
        elif prop_def == const.TYPE_STRING and not isinstance(val, basestring):
            return False
        elif isinstance(prop_def, list) and not val in prop_def:
            return False
    return True

def _prop_column_type(prop_def):
    if isinstance(prop_def, list):
        return const.TYPE_INT
    else:
        return prop_def

def _column_type_from_name(column_name):
    return column_name.split('_')[0]

class InvalidEvent(Exception):
    pass

class EventNotDefined(Exception):
    pass

class PropertyTypeConflict(Exception):
    def __init__(self, event_name, prop_name, column_type):
        err_msg = "Type conflicts in {}.{}. DB column type is {}".format(event_name, prop_name, column_type)
        super(PropertyTypeConflict, self).__init__(err_msg)

class EventSchema(object):
    MAPPING_KEY_PROP = 'property'
    MAPPING_KEY_COLUMN = 'column'

    MAPPING_TABLE = 'event_mapping'
    MAPPING_TABLE_COLUMNS = [
        {'name': 'id', 'type': 'int', 'primary_key':True},
        {'name': 'event_name', 'type': 'string'},
        {'name': 'property', 'type': 'string'},
        {'name': 'column_name', 'type': 'string'},
    ]

    def __init__(self, db_store):
        self._db = db_store
        self.common_properties = {}
        self.events = {}
        self.meta = _meta_defaults.copy()
        self.db_mappings = {}

    def load_from_file(self, schema_file):
        with open(schema_file) as f:
            config = yaml.load(f)
        self.common_properties = config.get('common_properties', {})
        self.events = config.get('events', {})
        if 'meta' in config:
            self.meta.update(config['meta'])
        self.update_mapping_table()

    def update_mapping_table(self):
        if not self._db.table_exists(self.MAPPING_TABLE):
            self._db.create_table(self.MAPPING_TABLE, self.MAPPING_TABLE_COLUMNS)
        event_names = self.list()
        to_add = []
        for event_name in event_names:
            mapping = self._get_mapping(event_name)
            schema = self.get_schema(event_name, only_props=True, include_common_properties=False)
            for prop_name, prop_def in schema.iteritems():
                column_type_def = _prop_column_type(prop_def)
                if prop_name in mapping:
                    column_type_db = _column_type_from_name(mapping[prop_name])
                    if column_type_def != column_type_db:
                        raise PropertyTypeConflict(event_name, prop_name, column_type_db)
                else:
                    column_name = self._find_column(column_type_def, mapping.values())
                    to_add.append({'event_name': event_name, 'property': prop_name, 'column_name': column_name})
        self._db.bulk_insert(self.MAPPING_TABLE, to_add, DistStore.DIST_TYPE_PRIMARY)
        # Invalid db_mapping cache
        self.db_mappings = {}

    def _get_mapping(self, event_name, key=MAPPING_KEY_PROP):
        if not event_name in self.db_mappings:
            rows = self._db.select(self.MAPPING_TABLE, {'event_name': event_name}, DistStore.DIST_TYPE_PRIMARY)
            print 'rows', rows
            self.db_mappings[event_name] = {
                'property': {row['property']:row['column_name'] for row in rows},
                'column': {row['column_name']:row['property'] for row in rows}
            }
        return self.db_mappings[event_name][key].copy()

    def _find_column(self, column_type, used_columns):
        max_cols = self.meta.get('{}_columns'.format(column_type.lower()))
        for i in xrange(max_cols):
            col_name = '{}_{}'.format(column_type, i)
            if col_name not in used_columns:
                return col_name
        return None

    def list(self):
        return self.events.keys()

    def get_schema(self, event_name, only_props=False, include_common_properties=True):
        if event_name not in self.events:
            raise EventNotDefined(event_name)
        schema = self.events[event_name]
        if only_props:
            schema = {k:v for k,v in schema.iteritems() if not k.startswith('_')}
        if include_common_properties:
            schema = schema.copy()
            schema.update(self.common_properties)
        return schema

    def validate(self, event):
        event_name = event.get('event_name')
        if not event_name:
            return False
        try:
            schema = self.get_schema(event['event_name'])
        except EventNotDefined:
            return False
        return _validate_event(event, schema)

    def create_event_table(self, table_name):
        event_table_columns = [
            {'name': 'id', 'type': const.TYPE_INT, 'primary_key': True},
            {'name': 'event_name', 'type': const.TYPE_STRING},
            {'name': 'event_time', 'type': const.TYPE_INT},
        ]
        # Common properties to columns
        event_table_columns.extend([
            {'name': name, 'type': _prop_column_type(prop)}
            for name, prop in self.common_properties.iteritems()
        ])
        # Custom properties slots
        gen_cols = lambda col_type, count: [
            {'name': '{}_{}'.format(col_type, i), 'type': col_type}
            for i in xrange(count)]
        event_table_columns.extend(gen_cols(const.TYPE_INT, self.meta['int_columns']))
        event_table_columns.extend(gen_cols(const.TYPE_FLOAT, self.meta['float_columns']))
        event_table_columns.extend(gen_cols(const.TYPE_STRING, self.meta['string_columns']))

        print 'create_event_table', table_name, event_table_columns
        self._db.create_table(table_name, event_table_columns)

    def to_db_record(self, event):
        '''
        Return a DB record from an event object.
        Every event object needs be converted to a DB record before saving to DB.
        '''
        if not self.validate(event):
            raise InvalidEvent(event)
        event_name = event['event_name']
        schema = self.get_schema(event_name)
        db_mapping = self._get_mapping(event_name)
        db_mapping.update({prop:prop for prop in self.common_properties})
        db_record = {
            'event_name': event_name,
            'event_time': event.get('event_time', int(time.time()))
        }
        for prop, val in event['properties'].iteritems():
            prop_def = schema[prop]
            column_name = db_mapping[prop]
            if isinstance(prop_def, list):
                # for enum properties, store hashed string in DB
                db_record[column_name] = hash(val)
            else:
                db_record[column_name] = val
        return db_record

    def from_db_record(self, record):
        '''
        Return a human-readable event from a DB record
        '''
        record = record.copy()
        event_name = record.pop('event_name')
        event = {
            'event_name': event_name,
            'event_time': record.pop('event_time'),
        }
        mapping = self._get_mapping(event_name, key=self.MAPPING_KEY_COLUMN)
        event['properties'] = {
            mapping[col]: val
            for col, val in record.iteritems()
        }
        return event

    def select_db_table(self, event):
        '''
        Return DB table name for storing the event
        '''
        # TODO: Timezone support?
        d = datetime.fromtimestamp(event['event_time'])
        return 'events_{:04d}{:02d}{:02d}'.format(d.year, d.month, d.day)
