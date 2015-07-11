import time
from itertools import izip

import gevent
from repoze.lru import lru_cache

import metrix.store

from . import event

TABLE_LRU_SIZE = 1024
TABLE_LRU_TIMEOUT = 300

class Collector(object):
    def __init__(self):
        self._pending = []
        self._process_thread = gevent.spawn(self._process)
        self._shutdown = False
        self._table_exists_cache = {}

    def init(self, cfg):
        self._db = metrix.store.connect(cfg.databases)
        self._event_schema = event.EventSchema(self._db)
        self._event_schema.load_from_file(cfg.event_schema)

    def enque(self, events):
        invalid_events = []
        now = int(time.time())
        for e in events:
            if not self._event_schema.validate(e):
                invalid_events.append(e)
            else:
                if 'event_time' not in e:
                    e['event_time'] = now
                self._pending.append(e)
        return {'invalid_events': invalid_events}

    def _process(self):
        # Time interval between checking the pending queue.
        # Note, it only takes effect if the pending queue is empty at last check.
        waiting_time = 1.0
        while not self._shutdown:
            # In traditional threads, the following code causes problem due to
            # race condition. But it works in gevent because thread-switching 
            # only happens on I/O operations.
            processing = self._pending
            self._pending = []
            if not processing:
                gevent.sleep(waiting_time)
                continue
            events = [self._event_schema.to_db_record(e) for e in processing]
            tables = [self._event_schema.select_db_table(e) for e in processing]
            table_event_map = {}
            [table_event_map.setdefault(t, []).append(e) for t, e in izip(tables, events)]
            for table, events in table_event_map.iteritems():
                if not self._table_exists(table):
                    self._event_schema.create_event_table(table)
                self._db.bulk_insert(t, events)
    
    @lru_cache(TABLE_LRU_SIZE, timeout=TABLE_LRU_TIMEOUT)
    def _table_exists(self, table):
        return self._db.table_exists(table)

