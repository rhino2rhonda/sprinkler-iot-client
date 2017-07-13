import pymysql
import SprinklerGlobals as globals


DB_USER = globals.DB_USER
DB_PSWD = globals.DB_PSWD
DB_NAME = globals.DB_NAME


def get_connection():
    return pymysql.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )


def close_connection(conn):
    conn.close()
