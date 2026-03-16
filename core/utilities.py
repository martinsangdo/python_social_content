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
        draw.text((x, y), line, font=font, fill=fill)   #no border
        y += font.size + line_spacing

def draw_wrapped_text_with_border(draw, position, text, font, max_width, fill=(255,255,255), line_spacing=6):
    x, y = position
    lines = wrap_text(text, font, max_width, draw)

    for line in lines:
        draw.text((x, y), line, font=font, fill=fill,
            stroke_width=5,
            stroke_fill="black")
        y += font.size + line_spacing

def get_first_file(folder_path: str, extension: str) -> tuple[str, str] | None:
    """Returns (full_path, filename_without_extension) of the first file with the given extension."""
    import os
    ext = extension if extension.startswith(".") else f".{extension}"
    files = sorted(
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f)) and f.endswith(ext)
    )
    if not files:
        return None
    first_file = files[0]
    return os.path.join(folder_path, first_file), os.path.splitext(first_file)[0]

def rename_files(folder_path: str, extension: str, start_index: int = 1) -> None:
    """Rename all files in a folder with a specific extension, starting from a given index."""
    ext = extension if extension.startswith(".") else f".{extension}"
    files = sorted(
        f for f in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, f)) and f.endswith(ext)
    )

    for i, filename in enumerate(files, start=start_index):
        src = os.path.join(folder_path, filename)
        dst = os.path.join(folder_path, f"{i}{ext}")
        os.rename(src, dst)
        print(f"{filename} → {i}{ext}")