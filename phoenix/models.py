# models.py
# Copyright (C) 2013 the ClimDaPs/Phoenix authors and contributors
# <see AUTHORS file>
#
# This module is part of ClimDaPs/Phoenix and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

# TODO: refactor usage of mongodb etc ...

from pyramid.security import (
    Allow,
    Everyone,
    )

import uuid
import datetime

from pyesgf.search import SearchConnection
from pyesgf.multidict import MultiDict

import logging

log = logging.getLogger(__name__)

from .helpers import mongodb_conn, esgsearch_url

# mongodb ...
# -----------

def database(request):
    conn = mongodb_conn(request)
    return conn.phoenix_db

def add_job(request,
            identifier,
            wps_url,
            execution,
            user_id='anonymous',
            notes='',
            tags=''):
    db = database(request)
    db.jobs.save(dict(
        user_id = user_id, 
        uuid = uuid.uuid4().get_hex(),
        identifier = identifier,
        service_url = wps_url,
        status_location = execution.statusLocation,
        status = execution.status,
        start_time = datetime.datetime.now(),
        end_time = datetime.datetime.now(),
        notes = notes,
        tags = tags,
    ))
    log.debug('count jobs = %s', db.jobs.count())

def get_job(request, uuid):
    db = database(request)
    job = db.jobs.find_one({'uuid': uuid})
    return job

def update_job(request, job):
    db = database(request)
    db.jobs.update({'uuid': job['uuid']}, job)

def num_jobs(request):
    db = database(request)
    return db.jobs.count()

def drop_jobs(request):
    db = database(request)
    db.jobs.drop()

def jobs_by_userid(request, user_id='anonymous'):
    db = database(request)
    return db.jobs.find( dict(user_id=user_id) )


# esgf search ....
# ----------------

def esgf_search_conn(request, distrib=True):
    return SearchConnection(esgsearch_url(request), distrib=distrib)
    
def esgf_search_context(request, query='*', distrib=True, replica=False, latest=True):
    conn = esgf_search_conn(request, distrib)
    ctx = conn.new_context( replica=replica, latest=latest, query=query)
    return ctx

def esgf_aggregation_search(ctx):
    log.debug("datasets found = %d", ctx.hit_count)
    if ctx.hit_count == 0:
        return []
    aggregations = []
    for result in ctx.search():
        agg_ctx = result.aggregation_context()
        log.debug('opendap num files = %d', agg_ctx.hit_count)
        for agg in agg_ctx.search():
            # filter with selected variables
            ok = False
            variables = ctx.facet_constraints.getall('variable')
            log.debug('variables in query: %s', variables)
            if len(variables) > 0:
                for var_name in variables:
                    if var_name in agg.json.get('variable', []):
                        ok = True
                        break
                if not ok: continue

            aggregations.append( (agg.opendap_url, agg.aggregation_id) )
    return aggregations

def esgf_file_search(ctx, start, end):
    from dateutil import parser
    start_date = parser.parse(start)
    end_date = parser.parse(end)
    start_str = '%04d%02d%02d' % (start_date.year, start_date.month, start_date.day)
    end_str = '%04d%02d%02d' % (end_date.year, end_date.month, end_date.day)

    log.debug("filter from=%s, to=%s", start_str, end_str)
    
    log.debug("datasets found = %d", ctx.hit_count)
    files = []
    for result in ctx.search():
        file_ctx = result.file_context()
        log.debug("files found = %d", file_ctx.hit_count)

        query_dict = MultiDict()
        query_dict['type'] = 'File'
        query_dict.extend(file_ctx.facet_constraints)
        query_dict.extend(ctx.facet_constraints)

        log.debug('before sending query ...')
        response = ctx.connection.send_search(limit=file_ctx.hit_count, query_dict=query_dict)
        log.debug('got query response')
        docs = response['response']['docs']
        for doc in docs:
            download_url = None
            for encoded in doc['url']:
                url, mime_type, service = encoded.split('|')
                if 'HTTPServer' in service:
                    download_url = url
                    break
            if download_url == None:
                continue
            filename = doc['title']

            # filter with time constraint
            index = filename.rindex('-')
            f_start = filename[index-8:index]
            f_end = filename[index+1:index+9]
            # match overlapping time range
            if f_end >= start_str and f_start <= end_str:
                files.append( (download_url, filename) )
    return files
