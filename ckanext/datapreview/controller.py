import os
import sys
import logging
import operator
import collections
from ckan.lib.base import (BaseController, c, g, render, request, response, abort)
from pylons import config
import sqlalchemy
from sqlalchemy import func, cast, Integer
import ckan.model as model

log = logging.getLogger('ckanext.datapreview')


from ckanext.datapreview.lib import AttributeDict
from ckanext.datapreview.lib.helpers import proxy_query, ProxyError


class DataPreviewController(BaseController):

    def index(self, id):
        resource = model.Resource.get(id)
        if not resource or resource.state != 'active':
            return ""

        try:
            result = proxy_query(resource, resource.url, {'type': 'csv'})
        except ProxyError as e:
            result = str(e)

        return result


    def serve(self, path):
        root = os.path.join(config.get('ckanext-archiver.archive_dir', '/tmp'),
                            path)
        if not os.path.exists(root):
            abort(404)

        return str(open(root).read())