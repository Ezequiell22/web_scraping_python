import pyodbc
import os
from dotenv import load_dotenv
load_dotenv()


def execute_select(query):

    try:

        server = os.environ['SERVER']
        database = os.environ['DATABASE']
        username = os.environ['USUARIO_DB']
        password = os.environ['SENHA_DB']

        connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"

        with pyodbc.connect(connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            result = cursor.fetchall()

        conn.close()
        return result
    except Exception as error:
        print(error)
        raise error


def execute_sql(query, values=None):
    server = os.environ['SERVER']
    database = os.environ['DATABASE']
    username = os.environ['USUARIO_DB']
    password = os.environ['SENHA_DB']

    connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"

    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()

        if values:
            # Verifica se é uma lista/tupla de valores
            if isinstance(values[0], (list, tuple)):
                cursor.executemany(query, values)
            else:
                cursor.execute(query, values)
        else:
            cursor.execute(query)

        conn.commit()
