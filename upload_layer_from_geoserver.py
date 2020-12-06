from geoserver.catalog import Catalog, FailedRequestError
from six import (
    string_types,
    reraise as raise_
)
import uuid, json, sys
from decimal import Decimal
from geoserver.store import CoverageStore, DataStore, datastore_from_index, \
    coveragestore_from_index, wmsstore_from_index
from geonode.layers.models import Layer, Attribute, Style
from geonode.security.views import _perms_info_json
from geonode.geoserver.helpers import set_attributes_from_geoserver, get_store, OGC_Servers_Handler
from django.conf import settings
from django.utils.translation import ugettext as _
from geonode.people.utils import get_valid_user

import requests
from requests.auth import HTTPBasicAuth


from General_modules import global_settings
from General_modules.module_GeoServer_access import get_url_user_pwd_geoserver, verify_datastore
from General_modules.module_logs import log_logs_file
from General_modules.module_DB import sqlExecute

gs_url, gs_rest_url, user, pwd = get_url_user_pwd_geoserver()
ogc_server_settings = OGC_Servers_Handler(settings.OGC_SERVER)['default']

gs_catalog = Catalog(gs_rest_url, user, pwd,
                        retries=ogc_server_settings.MAX_RETRIES,
                        backoff_factor=ogc_server_settings.BACKOFF_FACTOR)
    

# def test():
#     cat = gs_catalog
#     workspace = cat.get_workspace('geonode')
#     stores = cat.get_stores(workspaces='geonode')
#     stores_names = []
#     for s in stores:
#         stores_names.append(s.name)
    
#     return stores_names

# def test1(store, workspace_name='geonode'):
#     cat = gs_catalog
#     workspace = cat.get_workspace(workspace_name)

#     layer_names = Layer.objects.all().values_list('alternate', flat=True)
#     store = get_store(cat, store, workspace=workspace)
#     if store is None:
#         resources = []
#     else:
#         resources = cat.get_resources(stores=[store])
#     return [k.name for k in resources  if not '%s:%s' % (k.workspace.name, k.name) in layer_names]


def publish_resource_geonode(store, resource_name, workspace_name='geonode',  
                            execute_signals=True, user = "admin",
                            verbosity=1, permissions=None,
                            ignore_errors=True):

    output = {
        'stats': {
            'failed': 0,
            'updated': 0,
            'created': 0,
            'deleted': 0,
        },
        'layers': [],
        'deleted_layers': []
    }

    cat = gs_catalog

    owner = get_valid_user(user)

    workspace = cat.get_workspace(workspace_name)

    store = get_store(cat, store, workspace=workspace)
    if store is None:
        rsc = []
    else:
        resources = cat.get_resources(stores=[store])
        
        rsc = [k for k in resources
                        if '%s' % (k.name) in resource_name]

    for resource in rsc:
        name = resource.name
        the_store = resource.store
        workspace = the_store.workspace
        try:
            layer, created = Layer.objects.get_or_create(name=name, workspace=workspace.name, defaults={
                # "workspace": workspace.name,
                "store": the_store.name,
                "storeType": the_store.resource_type,
                "alternate": "%s:%s" % (workspace.name, resource.name),
                "title": resource.title or 'No title provided',
                "abstract": resource.abstract or u"{}".format(_('No abstract provided')),
                "owner": owner,
                "uuid": str(uuid.uuid4())
            })
            # print("laayer", layer)
            # print("created", created)
            layer.bbox_x0 = Decimal(resource.native_bbox[0])
            layer.bbox_x1 = Decimal(resource.native_bbox[1])
            layer.bbox_y0 = Decimal(resource.native_bbox[2])
            layer.bbox_y1 = Decimal(resource.native_bbox[3])
            layer.srid = resource.projection

            # sync permissions in GeoFence
            perm_spec = json.loads(_perms_info_json(layer))
            layer.set_permissions(perm_spec)

            # recalculate the layer statistics
            set_attributes_from_geoserver(layer, overwrite=True)

            # in some cases we need to explicitily save the resource to execute the signals
            # (for sure when running updatelayers)
            if execute_signals:
                layer.save()

            # Fix metadata links if the ip has changed
            if layer.link_set.metadata().count() > 0:
                if not created and settings.SITEURL not in layer.link_set.metadata()[0].url:
                    layer.link_set.metadata().delete()
                    layer.save()
                    metadata_links = []
                    for link in layer.link_set.metadata():
                        metadata_links.append((link.mime, link.name, link.url))
                    resource.metadata_links = metadata_links
                    cat.save(resource)

        except Exception as e:
            print("ERROR: ", e)
            if ignore_errors:
                status = 'failed'
                exception_type, error, traceback = sys.exc_info()
            else:
                if verbosity > 0:
                    msg = "Stopping process because --ignore-errors was not set and an error was found."
                    print(msg, file=sys.stderr)
                raise_(
                    Exception,
                    Exception("Failed to process {}".format(resource.name), e),
                    sys.exc_info()[2]
                )
        else:
            if created:
                if not permissions:
                    layer.set_default_permissions()
                else:
                    layer.set_permissions(permissions)

                status = 'created'
                output['stats']['created'] += 1
            else:
                status = 'updated'
                output['stats']['updated'] += 1


def publish_resource_geoserver(workspace, datastore, database, tableName, timeDimesionAttr):
    headers_xml = {'Content-Type': 'application/xml; charset=UTF-8'}
    xml = '<featureType><name>%s</name></featureType>'%(tableName)

    database_configuration = {
        "dataStore": {
            "name": "{}".format(datastore),
            "connectionParameters": {
                "entry": [
                    {"@key":"host","$":"{}".format(global_settings.POSTGRESQL_HOST)},
                    {"@key":"port","$":"{}".format(global_settings.POSTGRESQL_PORT)},
                    {"@key":"database","$":"{}".format(database)},
                    {"@key":"user","$":"{}".format(global_settings.POSTGRESQL_USERNAME)},
                    {"@key":"passwd","$":"{}".format(global_settings.POSTGRESQL_PASSWORD)},
                    {"@key":"dbtype","$":"postgis"},
                    {"@key": "Expose primary keys","$": "true"}
                ]
            }
        }
    }

    if verify_datastore(workspace, datastore, gs_rest_url, user, pwd, database_configuration):

        r = requests.post('{0}/workspaces/{1}/datastores/{2}/featuretypes'\
            .format(gs_rest_url, workspace,datastore),
                        auth=HTTPBasicAuth(user, pwd),
                        data=xml,
                        headers=headers_xml
                        )
        if r.status_code == 201:
            log_logs_file("Success uploading table {} to geoserver".format(tableName))

            if timeDimesionAttr != '':
                data_xml = '<featureType>\
                        <enabled>true</enabled>\
                        <metadata><entry key="time">\
                        <dimensionInfo>\
                        <enabled>true</enabled>\
                        <attribute>%s</attribute>\
                        <presentation>LIST</presentation>\
                        <units>ISO8601</units>\
                        <defaultValue>\
                        <strategy>MINIMUM</strategy>\
                        </defaultValue>\
                        </dimensionInfo>\
                        </entry></metadata>\
                        </featureType>'%(timeDimesionAttr)
                
                r = requests.put('{0}/workspaces/{1}/datastores/{2}/featuretypes/{3}'\
                    .format(gs_rest_url, workspace, datastore, tableName),
                                auth=HTTPBasicAuth(user, pwd),
                                data=data_xml,
                                headers=headers_xml
                                )
        else:
            log_logs_file("Error uploading table {} to geoserver".format(tableName))


def update_bbox_geoserver(workspace, datastore, tableName, location_col_name, database, db_user, db_pass, db_host, db_port):
    headers_xml = {'Content-Type': 'application/xml; charset=UTF-8'}
    headers_json_content = {'Content-Type': 'application/json'}
    headers_json_accept = {'accept': 'application/json'}

    r = requests.get('{0}/workspaces/{1}/datastores/{2}/featuretypes/{3}'\
                    .format(gs_rest_url, workspace, datastore, tableName),
                                auth=HTTPBasicAuth(user, pwd),
                                headers=headers_json_accept
                                )

    if r.status_code == 200:
        json_content = r.json()
        
        sql = '''SELECT ST_Extent("{0}"::geometry) as a from "{1}"'''.format(location_col_name, tableName)
        rec = sqlExecute(database, db_user, db_pass, db_host, db_port, sql, True)
        if rec['success']:
           bbox = rec['data'][0][0]
           bbox = bbox.split('BOX(')[1].split(')')[0].split(',')
           mins = bbox[0].split(' ')
           maxs = bbox[1].split(' ')

           json_content['featureType']['nativeBoundingBox']['minx'] = mins[0]
           json_content['featureType']['nativeBoundingBox']['miny'] = mins[1]
           json_content['featureType']['nativeBoundingBox']['maxx'] = maxs[0]
           json_content['featureType']['nativeBoundingBox']['maxy'] = maxs[1]

           json_content['featureType']['latLonBoundingBox']['minx'] = mins[0]
           json_content['featureType']['latLonBoundingBox']['miny'] = mins[1]
           json_content['featureType']['latLonBoundingBox']['maxx'] = maxs[0]
           json_content['featureType']['latLonBoundingBox']['maxy'] = maxs[1]

        r = requests.put('{0}/workspaces/{1}/datastores/{2}/featuretypes/{3}'\
                    .format(gs_rest_url, workspace, datastore, tableName),
                                auth=HTTPBasicAuth(user, pwd),
                                json=json_content,
                                headers=headers_json_content
                                )

        print(r.text, r.status_code)

