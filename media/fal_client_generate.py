# %% [markdown]
# <h2>Generate image/video with fal.ai</h2>

# %%
import os
import sys
import argparse

import fal_client

# Works in both .py files and Jupyter notebooks
try:
    base_path = os.path.dirname(__file__)  # works in .py files
except NameError:
    base_path = os.getcwd()                # fallback for Jupyter notebooks

core_path = os.path.abspath(os.path.join(base_path, '..', 'core'))
sys.path.append(core_path)

from dotenv import load_dotenv
load_dotenv(override=True)

# fal_client reads the key from this env var automatically
if not os.environ.get("FAL_KEY"):
    raise RuntimeError("FAL_KEY is not set. Add FAL_KEY=<your fal.ai api key> to .env")

# %%
DATA_FOLDER = '/Users/sangdo/Downloads/fal_output/'

IMAGE_MODEL = "fal-ai/flux/dev"
VIDEO_MODEL = "fal-ai/kling-video/v1.5/pro/image-to-video"


# %%
def _on_queue_update(update):
    if isinstance(update, fal_client.InProgress):
        for log in update.logs:
            print(log["message"])


def _download(url: str, dest_folder: str) -> str:
    import requests

    os.makedirs(dest_folder, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0]
    dest_path = os.path.join(dest_folder, filename)

    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return dest_path


# %%
def generate_image(prompt: str, model: str = IMAGE_MODEL, dest_folder: str = DATA_FOLDER, **extra_args):
    result = fal_client.subscribe(
        model,
        arguments={
            "prompt": prompt,
            **extra_args,
        },
        with_logs=True,
        on_queue_update=_on_queue_update,
    )

    return [_download(image["url"], dest_folder) for image in result["images"]]


# %%
def generate_video(prompt: str, image_url: str = None, model: str = VIDEO_MODEL, dest_folder: str = DATA_FOLDER, **extra_args):
    arguments = {"prompt": prompt, **extra_args}
    if image_url:
        arguments["image_url"] = image_url

    result = fal_client.subscribe(
        model,
        arguments=arguments,
        with_logs=True,
        on_queue_update=_on_queue_update,
    )

    return _download(result["video"]["url"], dest_folder)


# %%
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an image or video with fal.ai")
    parser.add_argument("mode", choices=["image", "video"], help="What to generate")
    parser.add_argument("prompt", help="Text prompt")
    parser.add_argument("--image-url", help="Source image URL, required for image-to-video models", default=None)
    parser.add_argument("--model", help="Override the fal.ai model id", default=None)
    args = parser.parse_args()

    if args.mode == "image":
        paths = generate_image(args.prompt, model=args.model or IMAGE_MODEL)
        print("Saved:", paths)
    else:
        path = generate_video(args.prompt, image_url=args.image_url, model=args.model or VIDEO_MODEL)
        print("Saved:", path)
#python3.10 fal_client_generate.py image "a cat is chasing a ball"