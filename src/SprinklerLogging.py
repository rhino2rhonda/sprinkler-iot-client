import logging.config
import json, os


# Creates the log directory if it does not exist
def create_log_dir():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    log_dir = os.path.join(dir_path, '..', 'logs')
    if not os.path.isdir(log_dir):
        os.mkdir(log_dir)


# Converts relative paths to absolute paths
def handle_relative_paths(log_dict):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    file_handler = log_dict['handlers']['file_handler']
    file_handler['filename'] = os.path.join(dir_path, file_handler['filename'])


# Configures application wide logging from JSON file
def configure_logging():
    create_log_dir()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    log_config_file = os.path.join(dir_path, 'logging.json')
    with open(log_config_file, 'r') as log_file:
        log_dict = json.load(log_file)
        handle_relative_paths(log_dict)
        logging.config.dictConfig(log_dict)
        logger = logging.getLogger(__name__)
        logger.info("Logging has been configured")
