from pathlib import Path


def list_video_in_path(folder_path):
    return list(Path(folder_path).glob("*.mp4"))

def list_audio_in_path(folder_path):
    return list(Path(folder_path).glob("*.mp3"))