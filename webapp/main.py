#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The only file which is directly executed. There's no reason to modify this
file.
"""

import web
import logging
import os
import sys

if __package__ in (None, ""):
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from webapp.settings import DEBUG
from webapp.urls import URLS
from webapp.app.tools.app_processor import (header_html, notfound, internalerror)
from webapp.app.controllers import db, put_session, put_app

logging.basicConfig(
    format='%(asctime)s:%(levelname)s:%(message)s', filename='/tmp/mtrackpro-web.log',
    datefmt='%Y-%m-%d %I:%M:%S', level=logging.DEBUG
)

web.config.debug = DEBUG

app = web.application(URLS, globals(), autoreload=False)
store = web.session.DBStore(db, 'sessions')
session = web.session.Session(app, store, initializer={'loggedin': False})

web.config.session_parameters['timeout'] = 300
web.config.session_parameters['ignore_expiry'] = False

put_session(session)

app.notfound = notfound
app.internalerror = internalerror
app.add_processor(web.loadhook(header_html))

if __name__ == '__main__':
    put_app(app)
    app.run()

application = app.wsgifunc()
