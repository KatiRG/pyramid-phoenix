from pyramid.security import authenticated_userid

import uuid
from datetime import datetime, timedelta
import pymongo
from phoenix.utils import localize_datetime
from dateutil import parser as datetime_parser

from phoenix import utils
from phoenix.security import Guest

import logging
logger = logging.getLogger(__name__)

def mongodb(registry):
    settings = registry.settings
    client = pymongo.MongoClient(settings['mongodb.host'], int(settings['mongodb.port']))
    return client[settings['mongodb.db_name']]

def auth_protocols(request):
    # TODO: refactor auth settings handling
    settings = request.db.settings.find_one()
    protocols = ['esgf', 'openid', 'ldap', 'oauth2']
    if settings is not None:
        if settings.has_key('auth'):
            if settings['auth'].has_key('protocol'):
                protocols = settings['auth']['protocol']
    return protocols

def get_user(request):
    userid = authenticated_userid(request)
    return request.db.users.find_one(dict(identifier=userid))

def add_user(
    request,
    login_id,
    email='',
    openid='',
    name='unknown',
    organisation='',
    notes='',
    group=Guest):
    user=dict(
        identifier =  str(uuid.uuid1()),
        login_id = login_id,
        email = email,
        openid = openid,
        name = name,
        organisation = organisation,
        notes = notes,
        group = group,
        creation_time = datetime.now(),
        last_login = datetime.now())
    request.db.users.save(user)
    return request.db.users.find_one({'identifier':user['identifier']})

def user_stats(request):
    num_unregistered = request.db.users.find({"group": Guest}).count()
    
    d = datetime.now() - timedelta(hours=3)
    num_logins_3h = request.db.users.find({"last_login": {"$gt": d}}).count()

    d = datetime.now() - timedelta(days=7)
    num_logins_7d = request.db.users.find({"last_login": {"$gt": d}}).count()

    return dict(num_users=request.db.users.count(),
                num_unregistered=num_unregistered,
                num_logins_3h=num_logins_3h,
                num_logins_7d=num_logins_7d)

def user_cert_valid(request, valid_hours=6):
    cert_expires = get_user(request).get('cert_expires')
    if cert_expires != None:
        timestamp = datetime_parser.parse(cert_expires)
        now = localize_datetime(datetime.utcnow())
        valid_hours = timedelta(hours=valid_hours)
        # cert must be valid for some hours
        if timestamp > now + valid_hours:
            return True
    return False

def load_settings(request):
    defaults = dict(solr_maxrecords = -1, solr_depth = 2)
    
    settings = request.db.settings.find_one()
    if not settings:
        settings = save_settings(request, defaults)
    for key in defaults.keys():
        if not key in settings:
            settings[key] = defaults[key]
    return settings

def save_settings(request, settings):
    request.db.settings.save(settings)
    return request.db.settings.find_one()
    





