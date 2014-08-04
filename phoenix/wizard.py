# views.py
# Copyright (C) 2013 the ClimDaPs/Phoenix authors and contributors
# <see AUTHORS file>
#
# This module is part of ClimDaPs/Phoenix and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php

import os
import datetime
import json
import yaml

from pyramid.view import view_config, forbidden_view_config
from pyramid.httpexceptions import HTTPException, HTTPFound, HTTPNotFound
from pyramid.security import authenticated_userid
from pyramid_deform import FormView, FormWizard, FormWizardView

import deform
from deform.form import Button
from deform import widget

import colander
from colander import Range, Invalid, null

from mako.template import Template

from owslib.wps import WebProcessingService

from .exceptions import TokenError
import models

from .wps import WPSSchema, execute_restflow, search_local_files

from .widget import (
    EsgSearchWidget,
    EsgFilesWidget,
    FileSearchWidget,
    WizardStatesWidget
    )


import logging
logger = logging.getLogger(__name__)

# constants for workflow steps
# TODO: need a better and dynamic way for this
SELECT_WPS = 0
SELECT_PROCESS = 1
DEFINE_PROCESS = 2
SELECT_SOURCE = 3
SEARCH_INPUT = 4
SELECT_INPUT = 5
DEFINE_ACCESS = 6

# csw function
def search_csw_files(csw, filter):
    logger.debug('filter=%s', filter)
    keywords = [k for k in map(str.strip, str(filter).split(' ')) if len(k)>0]
    
    files = []
    try:
        csw.getrecords(keywords=keywords)
        logger.debug('csw results %s', csw.results)
        for rec in csw.records:
            myrec = csw.records[rec]
            title = "%s (%s, %s)" % (myrec.title, myrec.subjects, myrec.abstract)
            files.append( (csw.records[rec].identifier, title) )
    except:
        files = []
        logger.exception('retrieving files failed! filter=%s', filter)
    return files

# select wps process
# ------------------

@colander.deferred
def deferred_choose_process_widget(node, kw):
    request = kw.get('request')
    wizard_state = kw.get('wizard_state', None)

    states = wizard_state.get_step_states()
    url = states.get(SELECT_WPS).get('url')
    wps = WebProcessingService(url)

    choices = []
    if wps is not None:
        logger.debug('using wps url=%s' % (wps.url))
        for process in wps.processes:
            if 'worker' in process.identifier:
                choices.append( (process.identifier, process.title) )
    return widget.RadioChoiceWidget(values = choices)

class SelectProcessSchema(colander.MappingSchema):
    process = colander.SchemaNode(
        colander.String(),
        widget = deferred_choose_process_widget)

# select data source schema
# -------------------------

@colander.deferred
def deferred_choose_datasource_widget(node, kw):
    request = kw.get('request')

    logger.debug('init datasource widget')
    
    choices = []
    for process in request.wps.processes:
        logger.debug('source process: %s', process.identifier)
        if 'source' in process.identifier:
            choices.append( (process.identifier, process.title) )
    return widget.RadioChoiceWidget(values = choices)

class SelectDataSourceSchema(colander.MappingSchema):
    appstruct = {}

    data_source = colander.SchemaNode(
        colander.String(),
        widget = deferred_choose_datasource_widget)

# search schema
# -----------------

def search_metadata(wps, wizard_state):
    if wps == None or wizard_state == None:
        return {}
    
    states = wizard_state.get_step_states()
    process_state = states.get(SELECT_PROCESS)
    process_id = process_state['process']

    from .helpers import get_process_metadata
    return get_process_metadata(wps, process_id)

def bind_search_schema(node, kw):
    logger.debug("bind esg search schema, kw=%s" % (kw))
    request = kw.get('request', None)
    wizard_state = kw.get('wizard_state', None)
    if request == None or wizard_state == None:
        return

    states = wizard_state.get_step_states()
    data_source_state = states.get(SELECT_SOURCE)
    data_source = data_source_state['data_source']

    metadata = search_metadata( request.wps, wizard_state)

    constraints =  metadata.get('esgfilter')
    logger.debug('constraints = %s', constraints )
    query = metadata.get('esgquery')
    logger.debug('query = %s', query )
    search = dict(facets=constraints, query=query)
    
    if 'esgf' in data_source:
        node.get('selection').title = 'ESGF Search'
        node.get('selection').default = json.dumps(search) 
        node.get('selection').widget = EsgSearchWidget(url="/esg-search")
    else:
        node.get('selection').title = 'Search Filter'
        node.get('selection').widget = FileSearchWidget()

    request.session['phoenix.wizard.files'] = None
    request.session.changed()


def esgsearch_validator(node, value):
    search = json.loads(value)
    if search.get('hit-count', 0) > 20:
        raise Invalid(node, 'More than 20 datasets selected: %r.' %  search['hit-count'])

class SearchSchema(colander.MappingSchema):
    appstruct = {}

    selection = colander.SchemaNode(
        colander.String(),
        validator = esgsearch_validator
        )

    def next_ok(self, request):
        return True

# select files schema
# -------------------

def bind_files_schema(node, kw):
    request = kw.get('request', None)
    
    wizard_state = kw.get('wizard_state', None)

    if request == None or wizard_state == None:
        logger.debug('not fetching files')
        return

    userdb = models.User(request)
    token = userdb.token(authenticated_userid(request))
    logger.debug('user token = %s' % (token))

    logger.debug('step num = %s', wizard_state.get_step_num())

    states = wizard_state.get_step_states()
    
    data_source_state = states.get(SELECT_SOURCE)
    data_source = data_source_state['data_source']

    search_state = states.get(SEARCH_INPUT)
    search = json.loads( search_state['selection'])

    logger.debug('fetching files')
    # TODO: cache results
    if 'esgf' in data_source:
        if 'opendap' in data_source:
            node.get('file_identifier').widget = EsgFilesWidget(
                url="/esg-search", search_type='Aggregation', search=search)
        else: # wget
            node.get('file_identifier').widget = EsgFilesWidget(
                url="/esg-search", search_type='File', search=search)
    elif 'filesystem' in data_source:
        choices = [(f, f) for f in search_local_files( request.wps, token, search['filter'])]
        node.get('file_identifier').widget = widget.CheckboxChoiceWidget(values=choices)
    elif 'csw' in data_source:
        choices = search_csw_files( request.csw, search['filter'] )
        node.get('file_identifier').widget = widget.CheckboxChoiceWidget(values=choices)
    else:
        logger.error('unknown datasource: %s', data_source)

   
class SelectFilesSchema(colander.MappingSchema):
    appstruct = {}
    
    file_identifier = colander.SchemaNode(
        colander.Set(),
        description = 'File Identifier',
        )

# opendap schema
# --------------

def bind_esg_access_schema(node, kw):
    logger.debug("bind access schema, kw=%s" % (kw))
    request = kw.get('request', None)
    wizard_state = kw.get('wizard_state', None)
    if request != None and wizard_state != None:
        states = wizard_state.get_step_states()
        data_source_state = states.get(SELECT_SOURCE)
        identifier = data_source_state['data_source']
        process = request.wps.describeprocess(identifier)
        node.add_nodes(process)
    if node.get('token', False):
        del node['token']
    if node.get('credentials', False):
        del node['credentials']
    if node.get('file_identifier', False):
        del node['file_identifier']

# wps process schema
# ------------------

def bind_wps_schema(node, kw):
    logger.debug("bind wps schema, kw=%s" % (kw))
    request = kw.get('request', None)
    wizard_state = kw.get('wizard_state', None)
    
    if request == None or wizard_state == None:
        return
  
    states = wizard_state.get_step_states()

    url = states.get(SELECT_WPS).get('url')
    wps = WebProcessingService(url)
    
    state = states.get(SELECT_PROCESS)
    identifier = state['process']

    process = wps.describeprocess(identifier)

    from .helpers import get_process_metadata
    metadata = get_process_metadata(wps, identifier)
    logger.debug('metadata = %s', metadata)
   
    node.add_nodes(process, metadata)

    if node.get('token', False):
        del node['token']
    if node.get('file_identifier', False):
        del node['file_identifier']

# summary schema
# --------------
    
class SummarySchema(colander.MappingSchema):
    appstruct = {}

    states = colander.SchemaNode(
        colander.String(),
        title = 'States',
        missing = '',
        widget=WizardStatesWidget())

# wizard
# ------

class MyFormWizardView(FormWizardView):
    from pyramid.security import authenticated_userid
     
    def check_token(self):
        userdb = models.User(self.request)
        user_id=authenticated_userid(self.request)
        
        if not userdb.is_token_valid(user_id):
            try:
                userdb.update(user_id, update_token=True, update_login=False)
            except TokenError as e:
                pass
    
    def check_credentials(self):
        user_id=authenticated_userid(self.request)
        userdb = models.User(self.request)
        user = userdb.by_id(user_id=user_id)
        cert_expires = user.get('cert_expires')

        valid_hours = 0
        
        try:
            from datetime import datetime
            from dateutil import parser as date_parser, relativedelta
            expires = date_parser.parse(cert_expires)
            now = datetime.utcnow()
            now = now.replace(tzinfo=expires.tzinfo)
            delta = relativedelta.relativedelta(expires, now)
            valid_hours = delta.hours
        except:
            logger.warn('could not get creds_expire')

        if valid_hours < 4:
            msg = "Credentials expire at <b>%s</b> UTC. Please update your <a href='/account'>Credentials</a>." % (cert_expires)
            self.request.session.flash(msg, queue='error')
    
    def __call__(self, request):
        self.request = request

        self.check_credentials()
        self.check_token()
        
        self.wizard_state = self.wizard_state_class(request, self.wizard.name)
        step = self.wizard_state.get_step_num()

        if step > len(self.wizard.schemas)-1:
            states = self.wizard_state.get_step_states()
            result = self.wizard.done(request, states)
            self.wizard_state.clear()
            return result
        form_view = self.form_view_class(request)
        schema = self.wizard.schemas[step]
        logger.debug('calling schema.bind on schema=%s' % (schema))
        self.schema = schema.bind(request=request, wizard_state=self.wizard_state)
        logger.debug('after wizard bind, schema = %s' % (self.schema))
        form_view.schema = self.schema
        buttons = []

        prev_disabled = False
        next_disabled = False
        cancel_disabled = False

        if hasattr(self.schema, 'prev_ok'):
            prev_disabled = not self.schema.prev_ok(request)

        if hasattr(self.schema, 'next_ok'):
            next_disabled = not self.schema.next_ok(request)

        prev_button = Button(name='previous', title='Previous',
                             disabled=prev_disabled)
        next_button = Button(name='next', title='Next',
                             disabled=next_disabled)
        done_button = Button(name='next', title='Done',
                             disabled=next_disabled)
        cancel_button = Button(name='cancel', title='Cancel',
                               disabled=cancel_disabled)

        if step > 0:
            buttons.append(prev_button)

        if step < len(self.wizard.schemas)-1:
            buttons.append(next_button)
        else:
            buttons.append(done_button)
        buttons.append(cancel_button)

        form_view.buttons = buttons
        form_view.next_success = self.next_success
        form_view.previous_success = self.previous_success
        form_view.previous_failure = self.previous_failure
        form_view.cancel_success = self.cancel
        form_view.cancel_failure = self.cancel
        form_view.show = self.show
        form_view.appstruct = getattr(self.schema, 'appstruct', None)
        logger.debug("before form_view, schema = %s" % (self.schema))
        return form_view()
      
    def cancel(self, validated):
        self.wizard_state.clear()
        return HTTPFound(location = self.request.path_url)

    def title(self):
        return getattr(self.schema, 'title', '...')

    def description(self):
        return getattr(self.schema, 'description', 'description')


def convert_states_to_nodes(request, states):
    userdb = models.User(request)
    token = userdb.token(authenticated_userid(request))
    credentials = userdb.credentials(authenticated_userid(request))
    
    source = dict(
        service = request.wps.url,
        identifier = str(states[SELECT_SOURCE].get('data_source')),
        input = ['token=%s' % (token), 'credentials=%s' % (credentials)],
        output = ['output'],
        sources = map(lambda x: [str(x)], states[SELECT_INPUT].get('file_identifier')),
        )
    # TODO: remove define access step
    if states[DEFINE_ACCESS].has_key('startindex'):
        source['input'].append('startindex=' + str(states[DEFINE_ACCESS].get('startindex', '')))
        source['input'].append('endindex=' + str(states[DEFINE_ACCESS].get('endindex', '')))
    if states[DEFINE_PROCESS].has_key('info_notes'):
        del(states[DEFINE_PROCESS]['info_notes'])   
    if states[DEFINE_PROCESS].has_key('info_tags'):
        del(states[DEFINE_PROCESS]['info_tags'])
    worker_input = map(lambda x: str(x[0]) + '=' + str(x[1]), states[DEFINE_PROCESS].items())
    # TODO: handle token for publisher ...
    worker_input.append('token=%s' % (token))
    worker = dict(
        service = states[SELECT_WPS].get('url'),
        identifier = str(states[SELECT_PROCESS].get('process')),
        input = worker_input,
        output = ['output'])
    nodes = dict(source=source, worker=worker)
    return nodes

class Done():
    form_view_class = FormView
    schema = SummarySchema
    states = None
    
    def __init__(self):
        pass
    
    def __call__(self, request, states):
        notes = states[DEFINE_PROCESS].get('info_notes', '')
        tags = states[DEFINE_PROCESS].get('info_tags', '')
        
        # convert states to workflow desc and run workflow
        nodes = convert_states_to_nodes(request, states)
        execution = execute_restflow(request.wps, nodes)

        models.add_job(
            request = request,
            user_id = authenticated_userid(request), 
            identifier = nodes['worker']['identifier'], 
            wps_url = request.wps.url, 
            execution = execution,
            notes = notes,
            tags = tags)
        
        form_view = self.form_view_class(request)
        form_view.schema = self.schema(title="Summary").bind()
        self.states = states
        form_view.appstruct = self.appstruct 
        result = form_view()
        return result

    def appstruct(self):
        return {'states': "Job submitted"}

@view_config(route_name='wizard',
             renderer='templates/wizard.pt',
             layout='default',
             permission='edit',
             )
def wizard(request):
    schemas = []
    catalogdb = models.Catalog(request)
    from schema import SelectWPSSchema
    schemas.append( SelectWPSSchema(title="Select WPS").bind(wps_list=catalogdb.all_as_tuple()))
    schemas.append( SelectProcessSchema(title='Select Process') )
    schemas.append( WPSSchema(
        info=True,
        title='Process Parameters', 
        after_bind=bind_wps_schema,
        ))
    schemas.append( SelectDataSourceSchema(title='Select Data Source') )
    schemas.append( SearchSchema(
        title='Search Input Files',
        after_bind=bind_search_schema,
        ))
    schemas.append( SelectFilesSchema(
        title='Select Files',
        after_bind=bind_files_schema,) )
    schemas.append( WPSSchema(
        title='Access Parameters', 
        after_bind=bind_esg_access_schema,
        ))
   
    wizard = FormWizard('Workflow', 
                        Done(), 
                        *schemas 
                        )
    view = MyFormWizardView(wizard)
    result = view(request)
    if type(result) is dict:
        result['title'] = view.title()
        result['description'] = view.description()
    return result


