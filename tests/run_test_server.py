#!/usr/bin/env python
from metrix import httpsrv

collector_config = 'collector_config.yml'
httpsrv.start_collector(collector_config)
