"""
video_wall.py  —  Build a 1920x1080 composite video from 12 clips.

Layout (matches mockup):
  - Title box      : top-left          (slot "title")
  - Thumbnails 1-5 : left column
  - Thumbnail  6   : bottom-left corner
  - Thumbnails 7-12: bottom row
  - Area 13        : main playback area (videos play here sequentially)

Behavior:
  - The 12 videos play one after another in area #13.
  - All 12 thumbnails are always visible in slots 1-12.
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
CANVAS_W, CANVAS_H = 1920, 1080
FPS                = 30
DELAY_SECONDS     = 2          # freeze on last frame between videos
HIGHLIGHT_COLOR   = (230, 50, 50)
HIGHLIGHT_WIDTH   = 6
BG_COLOR          = (255, 255, 255)
SHOW_EMPTY_SLOTS  = True       # gray placeholder boxes for unrevealed slots
FONT_PATH         = None       # e.g. "arial.ttf"; None -> PIL default
TITLE_FONT_SIZE   = 36

# --- Slot geometry (x, y, w, h), measured from the 1920x1080 mockup ---
TITLE_BOX = (10, 10, 265, 127)

THUMB_SLOTS = {
    1:  (10,   148, 265, 148),
    2:  (10,   302, 265, 148),
    3:  (10,   456, 265, 148),
    4:  (10,   610, 265, 148),
    5:  (10,   764, 265, 148),
    6:  (0,    925, 275, 148),
    7:  (283,  925, 265, 148),
    8:  (556,  925, 265, 148),
    9:  (829,  925, 265, 148),
    10: (1102, 925, 265, 148),
    11: (1375, 925, 265, 148),
    12: (1648, 925, 265, 148),
}

MAIN_AREA = (300, 10, 1610, 895)   # area #13

# ----------------------------------------------------------------------
# INPUTS  — edit these three lists (must all have 12 entries, same order)
# ----------------------------------------------------------------------
VIDEOS = [f"videos/video_{i:02d}.mp4" for i in range(1, 13)]
THUMBS = [f"thumbs/thumb_{i:02d}.jpg" for i in range(1, 13)]
TITLES = [f"Video {i}" for i in range(1, 13)]

OUTPUT_FILE = "output_wall.mp4"

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


def make_title_image(text, box):
    """Render the title text into an RGB image sized to the title box."""
    _, _, w, h = box
    img = Image.new("RGB", (w, h), (200, 200, 200))
    draw = ImageDraw.Draw(img)
    font = load_font(TITLE_FONT_SIZE)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((w - tw) / 2, (h - th) / 2), text, fill=(20, 20, 20), font=font)
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
    """Build one full-canvas segment: video #index playing in area 13."""
    video = VideoFileClip(VIDEOS[index])

    # main video + 2s freeze on its last frame
    main = fit_video(video, MAIN_AREA)
    last_frame = main.to_ImageClip(t=max(main.duration - 1 / FPS, 0))
    last_frame = last_frame.with_duration(DELAY_SECONDS).with_position(main.pos(0))
    seg_duration = main.duration + DELAY_SECONDS

    layers = [
        ColorClip((CANVAS_W, CANVAS_H), color=BG_COLOR).with_duration(seg_duration),
    ]

    # title
    title_img = make_title_image(TITLES[index], TITLE_BOX)
    layers.append(
        ImageClip(title_img)
        .with_duration(seg_duration)
        .with_position((TITLE_BOX[0], TITLE_BOX[1]))
    )

    # Progressive thumbnail reveal:
    #   - thumbs of already-finished clips (slots < index+1) stay visible
    #   - the CURRENT clip's thumb appears exactly when the clip ends
    #     (i.e. at the start of the 2s freeze), then carries into the
    #     next segments
    #   - future slots show an empty gray placeholder (set
    #     SHOW_EMPTY_SLOTS = False to hide them entirely)
    for slot, box in THUMB_SLOTS.items():
        i = slot - 1
        if i < index:
            # already revealed in a previous segment -> visible whole time
            img = make_thumb_image(THUMBS[i], box)
            layers.append(
                ImageClip(img).with_duration(seg_duration)
                .with_position((box[0], box[1]))
            )
        elif i == index:
            # placeholder while the clip plays...
            if SHOW_EMPTY_SLOTS:
                ph = make_thumb_image("", box)  # gray box, no image
                layers.append(
                    ImageClip(ph).with_duration(main.duration)
                    .with_position((box[0], box[1]))
                )
            # ...thumbnail pops in at the moment the clip ends
            img = make_thumb_image(THUMBS[i], box, highlight=True)
            layers.append(
                ImageClip(img).with_start(main.duration)
                .with_duration(DELAY_SECONDS)
                .with_position((box[0], box[1]))
            )
        else:
            # not yet revealed
            if SHOW_EMPTY_SLOTS:
                ph = make_thumb_image("", box)
                layers.append(
                    ImageClip(ph).with_duration(seg_duration)
                    .with_position((box[0], box[1]))
                )

    # video, then frozen last frame
    layers.append(main.with_start(0))
    layers.append(last_frame.with_start(main.duration))

    seg = CompositeVideoClip(layers, size=(CANVAS_W, CANVAS_H)).with_duration(seg_duration)
    if video.audio is not None:
        seg = seg.with_audio(video.audio)  # silence during the 2s freeze
    return seg


def main():
    assert len(VIDEOS) == len(THUMBS) == len(TITLES) == 12, "Need 12 of each."
    segments = [build_segment(i) for i in range(12)]
    final = concatenate_videoclips(segments, method="compose")
    final.write_videofile(
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
