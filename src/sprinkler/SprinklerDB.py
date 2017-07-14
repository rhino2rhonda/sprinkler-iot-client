import pymysql
import SprinklerGlobals as globals
import SprinklerUtils as utils
import threading
import time


# Globals
DB_HOST = globals.DB_HOST
DB_PORT = globals.DB_PORT
DB_USER = globals.DB_USER
DB_PSWD = globals.DB_PSWD
DB_NAME = globals.DB_NAME
DB_PING_INTERVAL = globals.DB_PING_INTERVAL


# Maintains a single DB connection and ensures synchronised access
# TODO: use DB agnostic ORM instead
@utils.singleton
class Connection(object):

    def __init__(self):
        
        self.logger = utils.get_logger()
        self.lock = threading.RLock()
        self.connection = self.create_connection()
        self.cursor = None

        # Start a keep alive daemon thread
        self.active = True
        self.keep_alive_thread = threading.Thread(target=self.keep_alive)
        self.keep_alive_thread.setDaemon(True)
        self.keep_alive_thread.start()

        self.logger.debug("Connection manager is up and running")

    def __call__(self):
        return self

    # Initializes a new BD connection
    def create_connection(self):

        self.logger.debug("Creating a new DB connection")
        conn = pymysql.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PSWD,
                db=DB_NAME,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
        
        self.logger.debug("Created a new DB connection")
        return conn


    # Closes DB connection
    def close_connections(self):
        self.logger.debug("Closing DB connection")
        self.active = False
        self.connection.close()


    # The context of the with block is set as a cursor to the existing connection
    # Only one thread can use the with block at one time
    def __enter__(self):
        self.lock.acquire()
        self.connection.begin()
        self.cursor = self.connection.cursor()
        return self.cursor


    # Cleans up the cursor and releases the lock after the with block terminates
    def __exit__(self, ex_type, ex_val, ex_trace):
        if ex_val is None:
            self.connection.commit()
        else:
            self.connection.rollback()
        self.cursor.close()
        self.cursor = None
        self.lock.release()


    # To be executed as a thread to ensure that the connection to the databse is kept alive
    def keep_alive(self):
        self.logger.debug("Keep alive thread is up and running")
        while self.active:
            time.sleep(DB_PING_INTERVAL)
            try:
                self.connection.ping()
            except Exception as ex:
                self.logger.error("Connection lost to DB. Will retry in %d secs" % DB_PING_INTERVAL)
        self.logger.debug("Keep alive thread will now be closed")

class xyz():

    def __init__(self):
        pass
