# -*- coding: utf-8 -*-
from flask import request, session, current_app
from flask.ext.babel import gettext
from flask.ext.login import current_user
from werkzeug.local import LocalProxy
from sqlalchemy.exc import OperationalError

from . import sample, wu, hss, gerok


registered_divisions = [sample.division, wu.division, hss.division,
                        gerok.division]


def init_divisions(app):
    app.extensions['divisions'] = [
        div for div in registered_divisions
        if not div.debug_only or app.debug
    ]


def init_context(app):
    for division in app.extensions['divisions']:
        division.init_context(app)


def division_from_name(name):
    for division in current_app.extensions['divisions']:
        if division.name == name:
            return division
    return None


def current_division():
    return division_from_name(session['division'])


def division_from_ip(ip):
    # TODO: return correct division based on IP (dummy method)
    return sample.division


def user_from_ip(ip):
    division = division_from_ip(ip)
    if division is not None:
        return division.user_class.from_ip(ip)
    else:
        return None


def current_user_supported():
    return LocalProxy(
        lambda: current_division().user_class.supported()
    )


def query_gauge_data():
    credit = {}
    try:
        if current_user.is_authenticated():
            user = current_user
        else:
            user = user_from_ip(request.remote_addr)
        credit['data'] = user.get_current_credit()
    except OperationalError:
        credit['error'] = gettext(u'Fehler bei der Abfrage der Daten')
    except AttributeError:
        credit['error'] = gettext(u'Diese IP gehört nicht '
                                  u'zu unserem Netzwerk')
    return credit
