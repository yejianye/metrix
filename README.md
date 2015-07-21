Metrix - A tools for metrics event collecting and analysis
==========================================================
*This project is still under development, and is not ready for release...*

We all know how important it is to log user events and analyze them to support product decisions. Metrix is an open source alternative to metrics analytics platform such as Mixpanel. At Slide Inc and Glow Inc, we've been building our internal metrics system for years. I think it would be benefical to open source those technologies.

Features
--------
Core Components:
- Collector: collecting events. Support REST API
- Analyzer: analyzing historical events. Provide a REST API similar to Mixpanel.
- Collector clients: It should be easy to develop a collector client given its REST API. A python client is written as a demonstration.

Supported backend:
- MySQL
- SQLite
Metrix support scale backend storage horizontally. New DB shards could be added and a tool for re-distribution data will be available. At Slide and Glow, we have stored billions of events in relational database, scalibility shouldn't be a problem for small business. We will abstract storage interface so that adding support for other relational database would be easy.

