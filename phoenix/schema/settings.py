import deform
import colander
from colander import Invalid

from phoenix.security import Admin, User, Guest

import logging
logger = logging.getLogger(__name__)

class UserSchema(colander.MappingSchema):
    choices = ((Admin, 'Admin'), (User, 'User'), (Guest, 'Guest'))
    
    name = colander.SchemaNode(
        colander.String(),
        title = "Name",
        missing = colander.drop,
        )
    email = colander.SchemaNode(
        colander.String(),
        validator = colander.Email(),
        missing = colander.drop,
        widget = deform.widget.TextInputWidget(readonly=True),
        )
    organisation = colander.SchemaNode(
        colander.String(),
        title = "Organisation",
        missing = colander.drop,
        )
    notes = colander.SchemaNode(
        colander.String(),
        title = "Notes",
        missing = colander.drop,
        )
    group = colander.SchemaNode(
        colander.String(),
        validator=colander.OneOf([x[0] for x in choices]),
        widget=deform.widget.RadioChoiceWidget(values=choices, inline=True),
        title='Group',
        description='Select Group')

class LdapSchema(colander.MappingSchema):
    server = colander.SchemaNode(
            colander.String(),
            title = 'Server',
            validator = colander.url,
            description = 'URI of LDAP server to connect to, e.g. "ldap://ldap.example.com"')
    bind = colander.SchemaNode(
            colander.String(),
            title = 'Bind',
            description = 'Bind to use for the LDAP connection, e.g. "CN=admin,DC=example,DC=com"')
    passwd = colander.SchemaNode(
            colander.String(),
            title = 'Password',
            description = 'Password for the LDAP bind',
            widget = deform.widget.PasswordWidget())
    base_dn = colander.SchemaNode(
            colander.String(),
            title = 'Base DN',
            description = 'DN where to begin the search for users, e.g. "CN=Users,DC=example,DC=com"')
    filter_tmpl = colander.SchemaNode(
            colander.String(),
            title = 'LDAP filter',
            description = """Used to filter the LDAP search.
                    Should always contain the placeholder "%(login)s".<br/>
                    Example for OpenLDAP: "(uid=%(login)s)"<br/>
                    Example for MS AD:    "(sAMAccountName=%(login)s)"<br/>
                    Have a look at http://pyramid-ldap.readthedocs.org/en/latest/
                    for more information.""")
    scope = colander.SchemaNode(
            colander.String(),
            title = 'Scope',
            description = 'Scope to search in',
            widget = deform.widget.SelectWidget(values = (
                ('ONELEVEL', 'One level'),
                ('SUBTREE',  'Subtree')))
            )
