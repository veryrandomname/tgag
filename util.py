import io
import json
import os
import random
import shutil
import string
from pathlib import Path
import os.path

def get_file_extension(filename):
    _, file_extension = os.path.splitext(filename)
    return file_extension[1:]


# path has to have a trailing slash /
def generate_unique_filename(path):
    filename = ''.join(random.choices(string.ascii_lowercase, k=15))
    if os.path.isfile(path + filename):
        return generate_unique_filename(path)
    else:
        return filename


def convert_gif_to_mp4(source_path, dest_path):
    os.system(
        f"ffmpeg -i  {source_path} -movflags faststart -pix_fmt yuv420p -vf 'scale=trunc(iw/2)*2:trunc(ih/2)*2' {dest_path}")


def convert_image_to_webp(source_path, dest_path):
    os.system(f"ffmpeg -i  {source_path} {dest_path}")


def apply_ffmpeg_to_stream(stream, ffmpeg_operation, input_file_extension, output_file_extension):
    tmp_directory_path = "/dev/shm/swepe_crawler/"
    tmp_filename = generate_unique_filename(f'{tmp_directory_path}')
    tmp_src = f'{tmp_directory_path}{tmp_filename}.{input_file_extension}'
    tmp_dst = f'{tmp_directory_path}{tmp_filename}.{output_file_extension}'
    with open(tmp_src, 'wb') as file:
        shutil.copyfileobj(stream, file)
        ffmpeg_operation(tmp_src, tmp_dst)
        if os.path.isfile(tmp_dst):
            with open(tmp_dst, 'rb') as file_dst:
                return io.BytesIO(file_dst.read())
        else:
            print("ERROR: some problem with ffmpeg it seems")


def gif_stream_to_mp4_stream(gif_stream):
    return apply_ffmpeg_to_stream(gif_stream, convert_gif_to_mp4, "gif", "mp4")


def image_stream_to_webp_stream(image_stream, input_file_extension):
    return apply_ffmpeg_to_stream(image_stream, convert_image_to_webp, input_file_extension, "webp")


def load_config():
    with open(str(Path.home()) + '/.config/swepe_config.json') as json_file:
        return json.load(json_file)
