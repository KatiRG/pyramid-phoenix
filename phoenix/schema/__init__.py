import deform
import colander
from colander import Invalid

from phoenix.widget import (
    TagsWidget,
    ESGFSearchWidget,
    )

import logging
logger = logging.getLogger(__name__)

class SwiftLoginSchema(colander.MappingSchema):
    username = colander.SchemaNode(
        colander.String(),
        title = "Username",
        description = "Your Swift Username: account:user",
        missing = '',
        default = '',
        )
    password = colander.SchemaNode(
        colander.String(),
        title = 'Password',
        missing = '',
        default = '',
        widget = deform.widget.PasswordWidget(size=30))


class UserProfileSchema(colander.MappingSchema):
    name = colander.SchemaNode(
        colander.String(),
        title = "Your Name",
        missing = '',
        default = '',
        )
    email = colander.SchemaNode(
        colander.String(),
        title = "EMail",
        validator = colander.Email(),
        missing = colander.drop,
        widget = deform.widget.TextInputWidget(),
        )
    organisation = colander.SchemaNode(
        colander.String(),
        title = "Organisation",
        missing = '',
        default = '',
        )
    notes = colander.SchemaNode(
        colander.String(),
        title = "Notes",
        missing = '',
        default = '',
        )


def esgfsearch_validator(node, value):
    import json
    search = json.loads(value)
    if search.get('hit-count', 0) > 100:
        raise Invalid(node, 'More than 100 datasets selected: %r.' %  search['hit-count'])

class ESGFSearchSchema(colander.MappingSchema):
    selection = colander.SchemaNode(
        colander.String(),
        validator = esgfsearch_validator,
        title = 'ESGF Search',
        widget = ESGFSearchWidget(url="/esg-search"))

class DoneSchema(colander.MappingSchema):
    @colander.deferred
    def deferred_favorite_name(node, kw):
        return kw.get('favorite_name', 'test')
    
    is_favorite = colander.SchemaNode(
        colander.Boolean(),
        title = "Save as Favorite",
        default = False,
        missing= False)
    favorite_name = colander.SchemaNode(
        colander.String(),
        title = "Favorite Name",
        default = deferred_favorite_name)

class UploadSchema(SwiftLoginSchema):
    
    container = colander.SchemaNode(colander.String())
    prefix = colander.SchemaNode(colander.String())
    #object_name = colander.SchemaNode(colander.String())
    source = colander.SchemaNode(
        colander.String(),
        description = 'URL to the source',
        validator = colander.url)

class PublishSchema(colander.MappingSchema):
    import uuid

    @colander.deferred
    def deferred_default_creator(node, kw):
        return kw.get('email')

    @colander.deferred
    def deferred_default_format(node, kw):
        return kw.get('format', "application/x-netcdf")
        
    identifier = colander.SchemaNode(
        colander.String(),
        default = uuid.uuid4().get_urn())
    title = colander.SchemaNode(colander.String())
    abstract = colander.SchemaNode(
        colander.String(),
        missing = '',
        default = '',
        validator = colander.Length(max=150),
        widget = deform.widget.TextAreaWidget(rows=2, cols=80))
    creator = colander.SchemaNode(
        colander.String(),
        validator = colander.Email(),
        default = deferred_default_creator,)
    source = colander.SchemaNode(
        colander.String(),
        description = 'URL to the source',
        validator = colander.url)
    format = colander.SchemaNode(
        colander.String(),
        default = deferred_default_format,
        description = 'Format of your source. Example: NetCDF',
        )
    subjects = colander.SchemaNode(
        colander.String(),
        default = 'test',
        missing = 'test',
        description = "Keywords: tas, temperature, ...",
        widget = TagsWidget(),
        )
    rights = colander.SchemaNode(
        colander.String(),
        missing = 'Unknown',
        default = 'Free for non-commercial use',
        )



