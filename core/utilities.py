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

def wrap_text(text, font, max_width, draw):
    """
    Splits text into lines that fit within max_width
    """
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        w = draw.textlength(test_line, font=font)

        if w <= max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines

def draw_wrapped_text(draw, position, text, font, max_width, fill=(255,255,255), line_spacing=6):
    x, y = position
    lines = wrap_text(text, font, max_width, draw)

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill)
        y += font.size + line_spacing