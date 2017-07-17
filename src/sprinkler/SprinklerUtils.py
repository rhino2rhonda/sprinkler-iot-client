# Custom exception
class SprinklerException(Exception):

    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


# Deocrator for singleton classes
def singleton(class_):
    instance = class_()
    return instance()
