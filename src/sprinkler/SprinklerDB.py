import pymysql
import SprinklerGlobals as globals

DB_HOST = globals.DB_HOST
DB_PORT = globals.DB_PORT
DB_USER = globals.DB_USER
DB_PSWD = globals.DB_PSWD
DB_NAME = globals.DB_NAME


def get_connection():
    return pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PSWD,
            db=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )


def close_connection(conn):
    conn.close()
