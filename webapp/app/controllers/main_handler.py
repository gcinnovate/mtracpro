# -*- coding: utf-8 -*-

"""This module contains the main handler of the application.
"""

import web
from . import render
from . import csrf_protected, db, get_session, put_session, allDistricts
from webapp.app.tools.utils import auth_user, audit_log


class Index:
    def GET(self):
        l = locals()
        del l['self']
        return render.login(**l)

    @csrf_protected
    def POST(self):
        session = get_session()
        params = web.input(username="", password="")
        username = params.username
        password = params.password
        r = auth_user(db, username, password)
        if r[0]:
            session.loggedin = True
            info = r[1]
            session.name = info.firstname + " " + info.lastname
            session.username = username
            session.sesid = info.id
            session.role = info.role
            session.districts = info.districts
            # districts_string to be used in a SIMILAR TO statment while getting reports from requests table
            session.districts_string = '|'.join(['%s' % allDistricts[d] for d in info.districts])
            print(session.districts_string)
            session.districts_array = str([int(x) for x in info.districts]).replace(
                '[', '{').replace(']', '}').replace('\'', '\"')
            session.criteria = ""
            user_perms = []
            perms = db.query(
                "SELECT codename FROM permissions WHERE id IN "
                " (SELECT permission_id FROM user_permissions WHERE user_id = $user_id)", {'user_id': info.id})
            for p in perms:
                user_perms.append(p['codename'])
            session.permissions = user_perms
            put_session(session)
            log_dict = {
                'logtype': 'Web', 'action': 'Login', 'actor': username,
                'ip': web.ctx['ip'], 'descr': 'User %s logged in' % username,
                'user': info.id
            }
            audit_log(db, log_dict)

            l = locals()
            del l['self']
            if info.role == 'District User':
                return web.seeother("/approve")
            else:
                return web.seeother("/approve")
        else:
            session.loggedin = False
            session.logon_err = r[1]
        l = locals()
        del l['self']
        return render.login(**l)


class Logout:
    def GET(self):
        session = get_session()
        log_dict = {
            'logtype': 'Web', 'action': 'Logout', 'actor': session.username,
            'ip': web.ctx['ip'], 'descr': 'User %s logged out' % session.username,
            'user': session.sesid
        }
        audit_log(db, log_dict)
        session.kill()
        return web.seeother("/")
