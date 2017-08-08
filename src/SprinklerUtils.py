from SprinklerConfig import config


# Computes the complete server API base url from config
def get_server_api_base():
    url = ''
    if config['SERVER_DNS']:
        url += config['SERVER_DNS']
    else:
        url += config['SERVER_PROTOCOL'] + config['SERVER_IP']
        if config['SERVER_PORT']:
            url += ':' + str(config['SERVER_PORT'])
    return url
