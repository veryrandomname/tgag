import os


def get_file_extension(filename):
    _, file_extension = os.path.splitext(filename)
    return file_extension[1:]
