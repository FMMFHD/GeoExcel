import psycopg2
import json
import math
import datetime
import pandas
import requests
from requests.auth import HTTPBasicAuth

from GeoExcel.upload_layer_from_geoserver import publish_resource_geonode, publish_resource_geoserver, update_bbox_geoserver
from GeoExcel.helpers import checkPointType
from GeoExcel.module_excel import copy_excel_database
from General_modules.module_DB import sqlExecute, foreignkeyTable, columnNamesOfTable
from General_modules import global_settings




def createView(Database, db_user, db_passwrod, db_host, db_port, foreignOptions):
    """
        Create a view that connects two or more tables
    """

    tableName = foreignOptions[0]['table']

    from_args = '"%s"'%(tableName)
    select_args = ''

    columnNames = {}

    foreignTables = []
    for opts in foreignOptions:
        f_Name = opts['f_table']
        foreignTables.append(f_Name)
        aux = columnNamesOfTable(Database, f_Name, db_user, db_passwrod, db_host, db_port)
        aux.remove(opts['f_col'])
        columnNames[f_Name] = aux
        from_args += ' INNER JOIN "{1}" ON "{0}"."{2}" = "{1}"."{3}"'.format(tableName, f_Name, opts['col'], opts['f_col'])

    aux = columnNamesOfTable(Database, foreignOptions[0]['table'], db_user, db_passwrod, db_host, db_port)

    for key in columnNames:
        f_keys = foreignkeyTable(Database, key, db_user, db_passwrod, db_host, db_port)
        for f_key in f_keys:
            if f_key['f_table'] in foreignTables:
                columnNames[key].remove(f_key['col'])
        for val in columnNames[key]:
            select_args += '"%s"."%s",'%(key, val)

    for val in aux:
        select_args += '"%s"."%s",'%(tableName, val)

    sql = """CREATE VIEW %s_view as SELECT %s FROM %s """%(tableName, select_args[:-1], from_args)

    # print(sql)

    rec = sqlExecute(Database, db_user, db_passwrod, db_host, db_port, sql, False)
    
    if rec['success']:
        return "%s_view"%(tableName)

    return tableName


def save_layer(tableName, timeDimesionAttr):
    """
        After inserting the table in the database, the geoserver does not automatically create the layer.
        After creating the layer, it is not sent to the geonode automatically.

        So the publication is done manually. 
    """
    datastore_name = global_settings.GEOSERVER_DATABASE_NAME
    database_name = global_settings.GENERIC_SAVE_EXCEL_DB

    publish_resource_geoserver('geonode', datastore_name, database_name, tableName, timeDimesionAttr)
    publish_resource_geonode(datastore_name, tableName)


def update_layer(tableName, location_col_name):
    datastore_name = global_settings.GEOSERVER_DATABASE_NAME
    database_name = global_settings.GENERIC_SAVE_EXCEL_DB
    db_user = global_settings.POSTGRESQL_USERNAME
    db_port = global_settings.POSTGRESQL_PORT
    db_host = global_settings.POSTGRESQL_HOST
    db_pass = global_settings.POSTGRESQL_PASSWORD
    update_bbox_geoserver('geonode', datastore_name, tableName, location_col_name, database_name, db_user, db_pass, db_host, db_port)
    
    publish_resource_geonode(datastore_name, tableName)


def InsertValues(path_to_excel, keys, data_UI, coordenatePoints, datum_code, tableName, DB_Name, db_user, db_password, db_host, db_port, foreignData = {}):
    """
       Upload the excel file to the database
    """

    information = {
        'foreignData': foreignData,
        'keys': keys,
        'data_UI': data_UI,
        'coordenatePoints': coordenatePoints,
        'datum_code': datum_code,
    }

    return copy_excel_database('', path_to_excel, DB_Name, tableName, '', save_to_DB, db_user, db_password, db_host, db_port, delete=False, information=information, create=False, cv=True)



def save_to_DB(tableName, dataframe, fileName, information):
    """
        Create the sql string to upload the excel file to the database
    """
    foreignData = information['foreignData']
    keys = information['keys']
    data_UI = information['data_UI']
    coordenatePoints = information['coordenatePoints']
    datum_code = information['datum_code']

    columns = dataframe.columns.ravel()

    sql = ""
    for i in range(len(dataframe[columns[0]])):
        value = ''
        keyscur = ''
        check = False
        Primary_key = True
        for name in columns:
            # try:
            #     check = math.isnan(dataframe[name][i])
            # except:
            #     check = False
            if pandas.isnull(dataframe[name][i]):
                check = True
                if name == data_UI['table2primaryKey']:
                    Primary_key = False
                    break
            
            if check:
                continue

            dataType = data_UI[name]
            if dataType == 'None':
                if name in foreignData.keys():
                    dataType = foreignData[name]['type']
            
            if 'timestamp' in dataType.lower():
                try:
                    datetime.datetime.strptime(dataframe[name][i],"%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    # print('Datetime break', e)
                    break
                else:
                    value += ''''%s', '''%(dataframe[name][i])
                    keyscur += '''"%s", '''%(keys[name])

            elif 'char' in dataType.lower():
                keyscur += '''"%s", '''%(keys[name])
                value += ''''%s', '''%(dataframe[name][i])

            elif 'int' in dataType.lower():
                keyscur += '''"%s", '''%(keys[name])
                value += "%s, "%(dataframe[name][i])

            elif 'float' in dataType.lower():
                keyscur += '''"%s", '''%(keys[name])
                value += "%s, "%(dataframe[name][i])

        if Primary_key:
            check=False
            if coordenatePoints:
                try:
                    check = math.isnan(dataframe[data_UI['longName']][i]) or math.isnan(dataframe[data_UI['latName']][i])
                except:
                    check = False

                if not check:
                    #Point( X Y ): X is longitude and Y latitude
                    lat = checkPointType(dataframe[data_UI['latName']][i], data_UI['latDegDec'])
                    longitude = checkPointType(dataframe[data_UI['longName']][i], data_UI['longDegDec'])
                    value +="ST_GeogFromText('SRID=%s;POINT(%f %f)'), "%(datum_code,longitude, lat)
                    keyscur += '''"%s", '''%(keys['coord'])

            if len(value) > 0 and len(keyscur) > 0:
                value = value[:len(value)-2]
                keyscur = keyscur[:len(keyscur)-2]

                sql += '''INSERT INTO "%s"(%s) VALUES (%s); '''%(tableName,keyscur,value)

    return sql
    

def getMappingTable(database, user, password, host, port, tableName):
    """
        Get the map to convert the excel to a new entry on a specific table
    """

    sql = """SELECT json FROM mapping_json WHERE tableName = '%s'"""%(tableName)

    rec = sqlExecute(database, user, password, host, port, sql, True)

    if rec['success']:
        if len(rec['data']) < 1:
            return {
                'success':False,
                'error':"There is no entry with the table_name = %s or this entry doesn't have the value on the column JSON"%(tableName)
            }
        return {
            'success':True,
            'data':rec['data'][0][0]
        }
        

    return rec


def createMappingTable(data, tableName, coordenatePoints, excelColumns, excelForeignCols, datum_code, tableView, Database, db_user, db_password, db_host, db_port):
    """
        Create the rule to later be more easier and quickly to upload the excle with the configorations to the database
    """
    my_data = {}

    my_data["tableView"] = tableView
    my_data["coordenatePoints"] = False
    my_data["coordenateInfo"] = {}
    my_data["variables"] = {}

    if coordenatePoints:
        aux_json = {}
        my_data["coordenatePoints"] = True
        name = data["nameCoord"]
        if name == "":
            name = "location"
        aux_json["colName"] = name
        aux_json["latName"] = data["latName"]
        aux_json["longName"] = data['longName']
        aux_json["latDegDec"] = data['latDegDec']
        aux_json["longDegDec"] = data['longDegDec']
        aux_json["datum"] = datum_code
        my_data["coordenateInfo"] = aux_json
    
    for name in excelColumns:
        if name == data['latName'] or name == data['longName']:
            continue

        dataType = data[name]
        if dataType == 'None':
            if name in excelForeignCols.keys():
                dataType = excelForeignCols[name]['type']
        
        my_data["variables"][name] = dataType
        

    sql = """INSERT INTO mapping_json(tableName, JSON) VALUES ('%s', '%s')"""%(tableName,json.dumps(my_data))

    resp_sql = sqlExecute(Database, db_user, db_password, db_host, db_port, sql, False)

    return resp_sql

def searchTablesByDatabase(database, user, password, host, port, mapping_json = False):
    """
        Get the list of tables from : 
            - the database if mapping_json == False
            - the table named mapping_json, otherwise
    """
    if mapping_json:
        sql = """SELECT tableName FROM mapping_json"""
    else:
        sql = """SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' and table_type='BASE TABLE'"""
    
    rec = sqlExecute(database, user, password, host, port, sql, True)

    if rec['success']:
        data = []

        if mapping_json:
            for aux in rec['data']:
                data.append(aux[0])
        else:
            for aux in rec['data']:	        
                if not ('spatial_ref_sys' in aux[0] or 'mapping_json' in aux[0]):
                    data.append(aux[0])

        data = sorted(data)
        return {
            'success':True,
            'data':data
        }
        
    else:
        return rec


def retrieveDatumNames(Database, db_user, db_password, db_host, db_port):
    """
        Get all the EPSG Datum Names from the epsg database
    """
    sql="""SELECT e.coord_ref_sys_name from epsg_coordinatereferencesystem as e 
        INNER JOIN spatial_ref_sys as s ON e.coord_ref_sys_code=s.srid"""

    rec = sqlExecute(Database, db_user, db_password, db_host, db_port, sql, True)

    if rec['success']:
        data = []

        for aux in rec['data']:
            if aux[0] != None:
                data.append(aux[0])

        data = sorted(data)
        return {
            'success':True,
            'data':data
        }
        
    else:
        return rec


def datumCode(name, Database, db_user, db_password, db_host, db_port):
    """
        Get the EPSG Datum Code for a specific name from the epsg database
    """
    sql = """e.coord_ref_sys_code from epsg_coordinatereferencesystem as e 
        INNER JOIN spatial_ref_sys as s ON e.coord_ref_sys_code=s.srid WHERE e.coord_ref_sys_name='%s'"""%(name)

    rec = sqlExecute(Database, db_user, db_password, db_host, db_port, sql, True)
    
    if rec['success']:
        data = rec['data'][0][0]


        return {
            'success':True,
            'data':data
        }
    
    return rec


def create_table_excel_general(tableName, columns, data_df, keys, data, coordenatePoints, datum_code, foreignData, Database, db_user, db_password, db_host, db_port):
    """
        Create a table according to the form and format of the excel
    """

    timeDimesionAttr = ''

    #Creating table as per requirement
    sql ='''CREATE TABLE "%s"( '''%(tableName)
    for name in columns:
        dataType = data[name]

        if name == data['latName'] or name == data['longName']:
            continue
        
        # Compare the information of selecting data keys with the information from choosing a foreign key
        if dataType == 'None':
            if name in foreignData.keys():
                dataType = foreignData[name]['type']
            else:
                return  [None, None, None, "The column %s doesn't have a data type"%(name)]
        else:
            if name in foreignData.keys():
                if dataType != foreignData[name]['type']:
                    return [None, None, None, "The data type of the column %s you choose is different from the foreign table"%(name)]

        if 'timestamp' in dataType.lower():
            timeDimesionAttr = name

        sql += """ "%s" %s"""%(name, dataType)
        if name == data['table2primaryKey']:
            sql+= ' PRIMARY KEY'
        sql+=','
        keys[name] = name
    
    if coordenatePoints:
        name = data['nameCoord']
        if name == '':
            name = 'location' 

        if 'coord' in foreignData.keys():
            if foreignData['coord']['type'] != 'geography(POINT)':
                return  [None, None, None, "The data type of the column coord should be GEOGRAPHY(POINT) but it is a foreign key to a foreign column with different data type"]

        sql += """ "%s" geography(POINT)"""%(name)
        if 'coord' == data['table2primaryKey']:
            sql+= ' PRIMARY KEY'
        sql += ","
        keys['coord']=name

    foreignOptions = []

    for name in foreignData:
        auxname = name
        if auxname == 'coord':
            auxname = data['nameCoord']
            if auxname == '':
                auxname = 'location'
        sql += """ FOREIGN KEY ("%s") REFERENCES %s (%s),"""%(auxname, foreignData[name]['table'], foreignData[name]['column'])
        foreignOptions.append({
            'f_col': foreignData[name]['column'],
            'col': auxname,
            'f_table': foreignData[name]['table'],
            'table': tableName
        })

    sql=sql[:len(sql)-1] + ')'

    resp_sql = sqlExecute(Database, db_user, db_password, db_host, db_port, sql, False)

    return [resp_sql, foreignOptions, timeDimesionAttr,'']