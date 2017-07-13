import os, errno

def make_fifo(path):
    try:
        os.mkfifo(path)
    except OSError as oe:
        if oe.errno != errno.EEXIST:
            raise

def read_fifo(path):
    with open(path, 'r') as fifo:
        full_data = ""
        while True:
            data = fifo.read()
            if len(data) == 0:
                break
            full_data += data
        return full_data


def write_fifo(path, data):
    with open(path, 'w') as fifo:
        fifo.write(data)
        fifo.flush()
