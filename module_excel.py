import pandas as pd

try:
    from module_logs import log_logs_file
    from module_DB import check_table, sqlExecute
except:
    from General_modules.module_logs import log_logs_file
    from General_modules.module_DB import check_table, sqlExecute


def copy_excel_database(directory, fileName, Database, tableName, tableCharacteristics, functionInsert, db_user, db_password, db_host, db_port, sheet_name=None, matrix=False, delete=True, create=True, information={}, cv=False):
    """
        Copy the data from the excel to a table in the database

        Steps:
            - Verify if the table exists
            - Open the Excel
            - Create the sql statements to upload the data
            - Execute the sql statements
    """

    if check_table(Database, tableName, tableCharacteristics, db_user, db_password, db_host, db_port, delete, create):
        path = directory + fileName
        if cv:
            if sheet_name is not None:
                dataframe = pd.read_csv(path, sheet_name=sheet_name)
            else:
                dataframe = pd.read_csv(path)
        
        else:
            if sheet_name is not None:
                dataframe = pd.read_excel(path, sheet_name=sheet_name)
            else:
                dataframe = pd.read_excel(path)

        if matrix:
            dataframe = dataframe.to_numpy()

        sql = functionInsert(tableName, dataframe, fileName, information)

        if sql != '':
            resp = sqlExecute(Database, db_user, db_password, db_host, db_port, sql, False)

            if not resp['success']:
                log_logs_file('Error: {}'.format(resp['data']))
            
            return resp
        else:
            log_logs_file("Sql statement is empty")

            return None
    

