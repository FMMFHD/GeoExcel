import pandas, re, psycopg2, math, unidecode, datetime, requests
import json, os, tempfile

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from GeoExcel.utils import retrieveDatumNames, datumCode, searchTablesByDatabase, createMappingTable, InsertValues, getMappingTable, save_layer, createView, create_table_excel_general, update_layer
from GeoExcel.helpers import convertToKnownDatatype
from General_modules.module_logs import log_error_file, log_logs_file
from General_modules.module_DB import constraintsTable, checkDataType
from General_modules import global_settings


@login_required
def excel_upload(request, template='upload/layer_upload.html'):
    """
        Receive a file, saved it on a tmp location, and redirect to this application
    """
    out = {'success': False}

    if request.method == 'POST':
        regex = re.compile(r"^%s$" % 'base_file')
        for name, value in request.FILES.items():
            match = regex.match(name)
            if match:
                fileName = '%s'%(value)
                excel_data_df = pandas.read_excel(value)

                fd, path = tempfile.mkstemp(dir=global_settings.PATH_TMP_FILES)

                try:
                    with os.fdopen(fd, 'w') as tmp:
                        # do stuff with temp file
                        excel_data_df.to_csv(tmp, index = None, header=True)
                except Exception as e:
                    log_error_file(str(e))
                finally:
                    tmp.close()

                status_code = 200
                out['success'] = True
                out['typeFile'] = path
                out['redirect'] = reverse('excel_begin')
                out['fileName'] = fileName
                break
        else:
            # Não recebeu um excel da maneira correta
            status_code = 400
    else:
        status_code = 400

    return HttpResponse(
        json.dumps(out),
        content_type='application/json',
        status=status_code)


@login_required
def excel_begin(request, template='GeoExcel/excel_begin.html', template_error='GeoExcel/error_page.html'):
    """
        Create the conditions for a user to choose between create a new table or add information to a existent table
    """

    rec = searchTablesByDatabase(global_settings.GENERIC_SAVE_EXCEL_DB, global_settings.POSTGRESQL_USERNAME, global_settings.POSTGRESQL_PASSWORD, global_settings.POSTGRESQL_HOST, global_settings.POSTGRESQL_PORT, True)

    if not rec['success']:
        return render(request, template_error,{
            "action":reverse('layer_upload'),
            "error": "%s"%(rec['data'])
        })

    fileName = request.POST['fileName']
    path = request.POST['path']
    return render(request,template, context={
        "path":path,
        "action_add":reverse('addNewEntries'),
        "action_create":reverse('configureTable'),
        "tables":rec['data'],
        "fileName":fileName
    })

@login_required
def configureTable(request, template='GeoExcel/excel_create.html', template_error='GeoExcel/error_page.html'):
    """
        Create the conditions for the user create is on table, by choosing the primary and foreing keys, also to create a new variable that is related with geographical locations
    """
    path = ''
    fileName = ''
    cols=[]
    datumName=[]
    columns = None
    if request.method == 'POST':
        path = request.POST['path']
        fileName = request.POST['fileName']
        tableName = request.POST['tableName']

        db_user = global_settings.POSTGRESQL_USERNAME
        db_password = global_settings.POSTGRESQL_PASSWORD
        db_host = global_settings.POSTGRESQL_HOST
        db_port = global_settings.POSTGRESQL_PORT 

        if tableName == '' or path == '' or fileName == '':
            return render(request, template_error,{
                "action":reverse('layer_upload'),
                "error": "One of the inputs is None"
            })

        tables_database_dict = searchTablesByDatabase(global_settings.GENERIC_SAVE_EXCEL_DB, db_user, db_password, db_host, db_port)

        if tables_database_dict['success']:
            if tableName in tables_database_dict['data']:
                return render(request, template_error,{
                    "action": reverse('layer_upload'),
                    "error": "Table {} already exists".format(tableName)
                })


        data_df = pandas.read_csv(path)
        columns = data_df.columns.ravel()
        for i in columns:
            cols.append(i)

        datum = retrieveDatumNames("epsg", db_user, db_password, db_host, db_port)

        if datum['success']:
            datumName = datum['data']
        else :
            return render(request, template_error,{
                "action":reverse('layer_upload'),
                "error": "%s"%(datum['data'])
            })

    return render(request,template, context={
        "path":path,
        'columns': cols,
        "action":"submit",
        "fileName":fileName,
        "tableName":tableName,
        "datum":datumName,
        "path_search_tables":reverse('searchTables'),
        "path_search_tablekey":reverse('searchTableKey'),
    })

@login_required
def searchTables(request, template='GeoExcel/error_page.html'):
    """
        Get all tables that exist on a database
    """
    out = {'success': False}
    status_code = 400
    if request.method == 'GET':

        rec = searchTablesByDatabase(global_settings.GENERIC_SAVE_EXCEL_DB, global_settings.POSTGRESQL_USERNAME, global_settings.POSTGRESQL_PASSWORD, global_settings.POSTGRESQL_HOST, global_settings.POSTGRESQL_PORT)

        if rec['success']:        
            status_code = 200
            out['success'] = True
            out['tables'] = rec['data']
        else:
            out['error'] = str(rec['data'])

    return HttpResponse(
        json.dumps(out),
        content_type='application/json',
        status=status_code)

@login_required
def searchTableKey(request, template='GeoExcel/error_page.html'):
    """
        Get all the primary or unique keys for a specific table
    """
    out = {'success': False}
    status_code = 400
    if request.method == 'GET':
        constraints =['PRIMARY KEY', 'UNIQUE']
        cols=[]
        dataType = []
        Database = global_settings.GENERIC_SAVE_EXCEL_DB
        db_user = global_settings.POSTGRESQL_USERNAME
        db_password = global_settings.POSTGRESQL_PASSWORD
        db_host = global_settings.POSTGRESQL_HOST
        db_port = global_settings.POSTGRESQL_PORT 

        for const in constraints:
            check = constraintsTable(request.GET['tableName'], const, Database, db_user, db_password, db_host, db_port)

            if check['success']:
                for data in check['data']:
                    cols.append(list(data)[0])
            else:
                out['error'] = str(check['data'])
                return HttpResponse(
                    json.dumps(out),
                    content_type='application/json',
                    status=status_code)

        for col in cols:
            check = checkDataType(request.GET['tableName'], col, Database, db_user, db_password, db_host, db_port)
            if check['success']:
                for data in check['data']:
                    dataType.append(convertToKnownDatatype(list(data)[0]))
            else:
                out['error'] = str(check['data'])
                return HttpResponse(
                    json.dumps(out),
                    content_type='application/json',
                    status=status_code)

        out['colname'] = cols
        out['datatype'] = dataType
        status_code = 200
        out['success'] = True

    return HttpResponse(
        json.dumps(out),
        content_type='application/json',
        status=status_code)


@login_required
def submitTable(request, template='GeoExcel/error_page.html'):
    """
        Convert the excel to a table form and upload to the database
    """
    if request.method == 'POST':
        coordenatePoints = False
        data_UI = request.POST
        keys = {}

        path = data_UI['path']
        tableName = data_UI['tableName']
        foreignKeys = int(data_UI['foreignKeys'])
        foreignData = {}
        data_dataframe = pandas.read_csv(path)
        columns = data_dataframe.columns.ravel()

        Database = global_settings.GENERIC_SAVE_EXCEL_DB
        db_user = global_settings.POSTGRESQL_USERNAME
        db_password = global_settings.POSTGRESQL_PASSWORD
        db_host = global_settings.POSTGRESQL_HOST
        db_port = global_settings.POSTGRESQL_PORT 

        if tableName == '' or path == '':
            return render(request, template,{
                "action":reverse('layer_upload'),
                "error": "One of the inputs is None"
            })

        tables_database_dict = searchTablesByDatabase(global_settings.GENERIC_SAVE_EXCEL_DB, db_user, db_password, db_host, db_port)

        if tables_database_dict['success']:
            if tableName in tables_database_dict['data']:
                return render(request, template,{
                    "action": reverse('layer_upload'),
                    "error": "Table {} already exists".format(tableName)
                })

        if ('None' != data_UI['latName'] and 'None' == data_UI['longName']) or ('None' == data_UI['latName'] and 'None' != data_UI['longName']):
            return render(request, template,{
                "action":reverse('layer_upload'),
                "error": "One of the fields of the 1st Step is None while the other field is not None"
            })
        
        datum_code = '4326'
        if data_UI['datum'] != 'None':
            datum=datumCode(data_UI['datum'], "epsg", db_user, db_password, db_host, db_port)
            if datum['success']:
                datum_code=datum['data']
        
        for i in range(1,foreignKeys+1):
            if ( not (data_UI['column3Step%s'%(i)] != 'None' and data_UI['tableForeign%s'%(i)] != 'None' and data_UI['columnForeign%s'%(i)] != 'None')) and \
                ( not (data_UI['column3Step%s'%(i)] == 'None' and data_UI['tableForeign%s'%(i)] == 'None' and data_UI['columnForeign%s'%(i)] == 'None')):

                return render(request, template,{
                    "action":reverse('layer_upload'),
                    "error": "One of the fields of the 3st Step is None while the other field is not None"
                })
        
        
        if('None' != data_UI['latName'] and 'None' != data_UI['longName']):
            coordenatePoints = True

        # Make a dicitionary that contains the information about the foreign keys, also if there is a misunderstanding it gives an error
        for i in range(1,foreignKeys+1):
            if (data_UI['column3Step%s'%(i)] == 'None' or data_UI['tableForeign%s'%(i)] == 'None' or data_UI['columnForeign%s'%(i)] == 'None' or data_UI['dataType%s'%(i)] == 'None'):
                continue
            # Se só quisermos que uma coluna só tenha uma foreign key
            if data_UI['column3Step%s'%(i)] in foreignData.keys():
                return render(request, template,{
                    "action":reverse('layer_upload'),
                    "error": "Choose the same column to be multiple column "
                })
            else:
                foreignData[data_UI['column3Step%s'%(i)]] = {
                    'type':data_UI['dataType%s'%(i)],
                    'table':data_UI['tableForeign%s'%(i)],
                    'column':data_UI['columnForeign%s'%(i)]
                }

        #Creating table as per requirement
        resp_sql, foreignOptions, timeDimesionAttr, error_msg = create_table_excel_general(tableName, columns, data_dataframe, keys, data_UI, coordenatePoints, datum_code, foreignData, Database, db_user, db_password, db_host, db_port)
        if error_msg != "":
            return render(request, template,{
                "action":reverse('layer_upload'),
                "error": error_msg
            })

        if not resp_sql['success']:
            error_msg = 'Error Creating Table: {}'.format(resp_sql['data'])
            log_logs_file(error_msg)
       
            return render(request, template,{
                "action":reverse('layer_upload'),
                "error": error_msg
            })

        if len(foreignOptions) > 0:
            tableView = createView(Database, db_user, db_password, db_host, db_port, foreignOptions)
        else:
            tableView = 'None'

        resp_sql = createMappingTable(data_UI, tableName, coordenatePoints, columns, foreignData, datum_code, tableView, Database, db_user, db_password, db_host, db_port)

        if not resp_sql['success']:
            error_msg = 'Error Insert Values: {}'.format(resp_sql['data'])
            log_logs_file(error_msg)
       
            return render(request, template,{
                "action":reverse('layer_upload'),
                "error": error_msg
            })

        resp_sql = InsertValues(path, keys, data_UI, coordenatePoints, datum_code, tableName, Database, db_user, db_password, db_host, db_port, foreignData)

        if resp_sql is None :
            error_msg = 'Error Insert Values: SQL is empty for some reason.'
            log_logs_file(error_msg)

            error_msg += '\nCaution: Check if the data type is chosen correctly.'
            return render(request, template,{
                "action":reverse('layer_upload'),
                "error": error_msg
            })
            
        if not resp_sql['success']:
            error_msg = 'Error Insert Values: {}'.format(resp_sql['data'])
            log_logs_file(error_msg)
       
            return render(request, template,{
                "action":reverse('layer_upload'),
                "error": error_msg
            })


        #Remove the tmp file
        os.remove(path)

        if tableView == 'None':
            save_layer(tableName, timeDimesionAttr)
        else:
            save_layer(tableView, timeDimesionAttr)

        return redirect('layer_upload')

    return render(request, template,{
        "action":reverse('layer_upload'),
        "error": "Wrong method to access %s"%(reverse('submitTable'))
    })

@login_required
def addNewEntries(request, template='GeoExcel/error_page.html'):
    """
        ADD new entries to a specific table
    """
    if request.method == 'POST':
        Database = global_settings.GENERIC_SAVE_EXCEL_DB
        db_user = global_settings.POSTGRESQL_USERNAME
        db_password = global_settings.POSTGRESQL_PASSWORD
        db_host = global_settings.POSTGRESQL_HOST
        db_port = global_settings.POSTGRESQL_PORT 
        
        path = request.POST['path']
        tableName = request.POST['tableName']
        rec = getMappingTable(Database, db_user, db_password, db_host, db_port, tableName)

        if not rec['success']:
            return render(request, template,{
                "action":reverse('layer_upload'),
                "error": "%s"%(rec['data'])
            })
        mapping = rec['data']
        data_df = pandas.read_csv(path)
        columns = data_df.columns.ravel()

        data = mapping['variables']

        data.update(mapping['coordenateInfo'])

        keys = {}

        if mapping['coordenatePoints']:
            datum_code = data["datum"]
            data[data['latName']] = 'None'
            data[data['longName']] = 'None'
            keys['coord'] = data['colName']
            location_col_name = data['colName']
        else:
            datum_code = 0
            location_col_name = None

        for name in columns:
            if mapping['coordenatePoints']:
                if name == data['latName'] or name == data['longName']:
                    continue
            keys[name] = name

        resp_sql = InsertValues(path, keys, data, mapping['coordenatePoints'], datum_code, tableName, Database, db_user, db_password, db_host, db_port)
       
        update_layer(tableName, location_col_name)

        #Remove the tmp file
        os.remove(path)


        if not resp_sql['success']:
            error_msg = 'Error Insert Values: {}'.format(resp_sql['data'])
            log_logs_file(error_msg)
       
            return render(request, template,{
                "action":reverse('layer_upload'),
                "error": error_msg
            })

        return redirect('layer_upload')
       

    return render(request, template, {
        "action":reverse('layer_upload'),
        "error": "Wrong method to access %s"%(reverse('addNewEntries'))
    })
