from pathlib import Path
import random

def list_video_in_path(folder_path):
    return list(Path(folder_path).glob("*.mp4"))

def list_audio_in_path(folder_path):
    return list(Path(folder_path).glob("*.mp3"))

def list_image_in_path(folder_path):
    return list(Path(folder_path).glob("*.png"))

def get_random_item(items):
    return random.choice(items)