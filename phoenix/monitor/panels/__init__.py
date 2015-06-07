from pyramid_layout.panel import panel_config

import logging
logger = logging.getLogger(__name__)

def job_details(request, job_id):
    job = request.db.jobs.find_one({'identifier': job_id})
    details = job.copy()
    from phoenix.utils import time_ago_in_words
    details['finished'] = time_ago_in_words(job.get('finished'))
    return details

@panel_config(name='monitor_details', renderer='../templates/panels/monitor_details.pt')
def details(context, request):
    job_id = request.session.get('job_id')
    return dict(job=job_details(request, job_id=job_id))

@panel_config(name='monitor_log', renderer='../templates/panels/monitor_log.pt')
def log(context, request):
    job_id = request.session.get('job_id')
    job = request.db.jobs.find_one({'identifier': job_id})
    return dict(log=job.get('log'))
