from pyramid_layout.panel import panel_config
from deform import Form, ValidationFailure
from phoenix import models

import logging
logger = logging.getLogger(__name__)

class ProfilePanel(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def appstruct(self):
        appstruct = models.get_user(self.request)
        if appstruct is None:
            appstruct = {}
        return appstruct

class AccountPanel(ProfilePanel):
    def generate_form(self):
        from phoenix.schema import UserProfileSchema
        form = Form(schema=UserProfileSchema(), buttons=('update',), formid='deform')
        return form
    
    def process_form(self, form):
        try:
            controls = self.request.POST.items()
            appstruct = form.validate(controls)
            user = models.get_user(self.request)
            for key in ['name', 'organisation', 'notes']:
                user[key] = appstruct.get(key)
            self.request.db.users.update({'email':models.user_email(self.request)}, user)
        except ValidationFailure, e:
            logger.exception('validation of form failed.')
            return dict(form=e.render())
        except Exception, e:
            logger.exception('update user failed.')
            self.request.session.flash('Update of your accound failed. %s' % (e), queue='danger')
        else:
            self.request.session.flash("Your account was updated.", queue='success')

    @panel_config(name='myaccount_profile', renderer='phoenix:templates/panels/form.pt')
    def panel(self):
        form = self.generate_form()
        if 'update' in self.request.POST:
            self.process_form(form)
        return dict(title="Profile", form=form.render( self.appstruct() ))

class ESGFPanel(ProfilePanel):
    def generate_form(self):
        from phoenix.schema import ESGFCredentialsSchema
        form = Form(schema=ESGFCredentialsSchema(), formid='deform')
        return form

    @panel_config(name='myaccount_esgf', renderer='phoenix:templates/panels/form.pt')
    def panel(self):
        form = self.generate_form()
        return dict(title="ESGF access token", form=form.render( self.appstruct() ))

class SwiftPanel(ProfilePanel):
    def generate_form(self):
        from phoenix.schema import SwiftSchema
        form = Form(schema=SwiftSchema(), formid='deform')
        return form

    @panel_config(name='myaccount_swift', renderer='phoenix:templates/panels/form.pt')
    def panel(self):
        form = self.generate_form()
        return dict(title="Swift access token", form=form.render( self.appstruct() ))
