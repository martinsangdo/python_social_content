"""
video_wall.py  —  Build a 1600x900 composite video from 10 clips.

Layout (matches mockup):
  - Title box      : top-left          (slot "title")
  - Thumbnails 1-5 : left column
  - Thumbnails 6-10: bottom row
  - Area 11        : main playback area (videos play here sequentially)

Behavior:
  - The 10 videos play one after another in area #11.
  - All 10 thumbnails are always visible in slots 1-10.
  - The currently playing video's thumbnail gets a red highlight border.
  - The title for the current video shows in the Title box.
  - After each video ends, its last frame freezes for DELAY_SECONDS,
    then the next video starts automatically.

Requirements:
  pip install moviepy pillow numpy
  (ffmpeg must be installed and on PATH)

Tested against moviepy >= 2.0 API. For moviepy 1.x see notes at bottom.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    VideoFileClip,
    ImageClip,
    CompositeVideoClip,
    ColorClip,
    concatenate_videoclips,
)

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
CANVAS_W, CANVAS_H = 1600, 900
FPS                = 30
DELAY_SECONDS     = 2          # freeze on last frame between videos
TITLE_INTRO       = 2          # seconds to show title before thumbnail
THUMB_INTRO       = 1          # seconds to show thumbnail before clip plays
HIGHLIGHT_COLOR   = (230, 50, 50)
HIGHLIGHT_WIDTH   = 3
BG_COLOR          = (255, 255, 255)
SHOW_EMPTY_SLOTS  = True       # gray placeholder boxes for unrevealed slots
FONT_PATH         = None       # e.g. "arial.ttf"; None -> PIL default
TITLE_FONT_SIZE   = 72         # used in main area during title intro
TITLE_SMALL_SIZE  = 28         # used in title box during playback

# --- Slot geometry (x, y, w, h), measured from the 1600x900 mockup ---
TITLE_BOX = (28, 10, 250, 80)

THUMB_SLOTS = {
    1:  (28,   100, 250, 150),
    2:  (28,   260, 250, 150),
    3:  (28,   420, 250, 150),
    4:  (28,   580, 250, 150),
    5:  (28,   740, 250, 150),
    6:  (310, 740, 250, 150),
    7:  (568,  740, 250, 150),
    8:  (826,  740, 250, 150),
    9:  (1083,  740, 250, 150),
    10: (1340, 740, 250, 150),
}

MAIN_AREA = (310, 10, 1280, 720)   # area #11

# ----------------------------------------------------------------------
# INPUTS  — edit these three lists (must all have 10 entries, same order)
# ----------------------------------------------------------------------

category = 'tom_cruise'
PROJECT_FOLDER = '/Users/sangdo/Downloads/movie-top-list/'
folder_path = PROJECT_FOLDER + 'clips/' + category + '/'

VIDEOS = [f for f in sorted(os.listdir(folder_path)) if f.endswith('.mp4') and not f.startswith('_output_wall')]
VIDEOS = [folder_path + f for f in VIDEOS]
THUMBS = [v.replace('.mp4', '_thumb.png') for v in VIDEOS]
TITLES = [f"Video {i}" for i in range(1, 11)]   #todo: set real titles here

OUTPUT_FILE = folder_path + "_output_wall.mp4"

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def load_font(size):
    if FONT_PATH:
        return ImageFont.truetype(FONT_PATH, size)
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def make_title_image(text, box, font_size=None, bg_color=(200, 200, 200), centered=False):
    """Render title text top-left in white; truncate with '...' if overflow."""
    _, _, w, h = box
    if font_size is None:
        font_size = TITLE_FONT_SIZE
    img = Image.new("RGB", (w, h), bg_color)
    draw = ImageDraw.Draw(img)
    font = load_font(font_size)
    display = text
    while display:
        bbox = draw.textbbox((0, 0), display, font=font)
        if bbox[2] - bbox[0] <= w:
            break
        display = display[:-1]
    if display != text:
        display = display[:-3] + '...'
    if centered and display:
        bbox = draw.textbbox((0, 0), display, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((w - tw) / 2, (h - th) / 2), display, fill=(255, 255, 255), font=font)
    else:
        draw.text((0, 0), display, fill=(255, 255, 255), font=font)
    return np.array(img)


def make_thumb_image(path, box, highlight=False):
    """Load thumbnail, letterbox-fit into slot, optional highlight border."""
    _, _, w, h = box
    canvas = Image.new("RGB", (w, h), (150, 150, 150))
    if os.path.exists(path):
        im = Image.open(path).convert("RGB")
        scale = min(w / im.width, h / im.height)
        nw, nh = int(im.width * scale), int(im.height * scale)
        im = im.resize((nw, nh), Image.LANCZOS)
        canvas.paste(im, ((w - nw) // 2, (h - nh) // 2))
    if highlight:
        d = ImageDraw.Draw(canvas)
        for k in range(HIGHLIGHT_WIDTH):
            d.rectangle([k, k, w - 1 - k, h - 1 - k], outline=HIGHLIGHT_COLOR)
    return np.array(canvas)


def fit_video(clip, box):
    """Resize a video clip to fit inside area #13 (letterboxed, centered)."""
    x, y, w, h = box
    scale = min(w / clip.w, h / clip.h)
    clip = clip.resized(scale)
    px = x + (w - clip.w) // 2
    py = y + (h - clip.h) // 2
    return clip.with_position((px, py))


def build_segment(index):
    """Build one full-canvas segment:
      - TITLE_INTRO s : title shown in main area on blank canvas
      - THUMB_INTRO s : thumbnail shown in main area
      - clip duration : video plays
      - DELAY_SECONDS : freeze on last frame
    """
    video = VideoFileClip(VIDEOS[index])
    main = fit_video(video, MAIN_AREA)

    t_title  = 0
    t_thumb  = TITLE_INTRO
    t_clip   = TITLE_INTRO + THUMB_INTRO
    t_freeze = t_clip + main.duration
    seg_duration = t_freeze + DELAY_SECONDS

    last_frame = main.to_ImageClip(t=max(main.duration - 1 / FPS, 0))
    last_frame = last_frame.with_duration(DELAY_SECONDS).with_position(main.pos(0))

    layers = [
        ColorClip((CANVAS_W, CANVAS_H), color=BG_COLOR).with_duration(seg_duration),
    ]

    # sidebar thumbnails
    slot_box = THUMB_SLOTS[index + 1]  # the sidebar slot for the current video
    for slot, box in THUMB_SLOTS.items():
        i = slot - 1
        if i < index:
            img = make_thumb_image(THUMBS[i], box)
            layers.append(
                ImageClip(img).with_duration(seg_duration)
                .with_position((box[0], box[1]))
            )
        elif i == index:
            # phase 1: title text in the slot
            title_slot_img = make_title_image(TITLES[index], box, font_size=TITLE_SMALL_SIZE,
                                              bg_color=(200, 200, 200), centered=True)
            layers.append(
                ImageClip(title_slot_img)
                .with_start(t_title)
                .with_duration(TITLE_INTRO)
                .with_position((box[0], box[1]))
            )
            # phase 2: thumbnail in the slot
            img = make_thumb_image(THUMBS[i], box)
            layers.append(
                ImageClip(img)
                .with_start(t_thumb)
                .with_duration(seg_duration - t_thumb)
                .with_position((box[0], box[1]))
            )
        else:
            if SHOW_EMPTY_SLOTS:
                ph = make_thumb_image("", box)
                layers.append(
                    ImageClip(ph).with_duration(seg_duration)
                    .with_position((box[0], box[1]))
                )

    # video starts after title + thumb intro, then frozen last frame
    layers.append(main.with_start(t_clip))
    layers.append(last_frame.with_start(t_freeze))

    seg = CompositeVideoClip(layers, size=(CANVAS_W, CANVAS_H)).with_duration(seg_duration)
    if video.audio is not None:
        seg = seg.with_audio(video.audio.with_start(t_clip))
    return seg


def main():
    assert len(VIDEOS) == len(THUMBS) == len(TITLES) == 10, "Need 10 of each."
    segments = [build_segment(i) for i in range(10)]
    final = concatenate_videoclips(segments, method="compose")
    final.write_videofile(  #around 6:30 mins for 1 video to complete
        OUTPUT_FILE,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        preset="medium",
    )


if __name__ == "__main__":
    main()

# ----------------------------------------------------------------------
# moviepy 1.x compatibility notes (if you're on moviepy==1.0.3):
#   from moviepy.editor import ...           (instead of `from moviepy import`)
#   clip.resized(s)        -> clip.resize(s)
#   clip.with_position(p)  -> clip.set_position(p)
#   clip.with_duration(d)  -> clip.set_duration(d)
#   clip.with_start(t)     -> clip.set_start(t)
#   clip.with_audio(a)     -> clip.set_audio(a)
# ----------------------------------------------------------------------
