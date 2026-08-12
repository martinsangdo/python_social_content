# %% [markdown]
# <h2>Generate image/video with replicate.com</h2>

# %%
import os
import sys
import argparse

import replicate

# Works in both .py files and Jupyter notebooks
try:
    base_path = os.path.dirname(__file__)  # works in .py files
except NameError:
    base_path = os.getcwd()                # fallback for Jupyter notebooks

core_path = os.path.abspath(os.path.join(base_path, '..', 'core'))
sys.path.append(core_path)

from dotenv import load_dotenv
load_dotenv(override=True)

# replicate client reads the key from this env var automatically
if not os.environ.get("REPLICATE_API_TOKEN"):
    raise RuntimeError("REPLICATE_API_TOKEN is not set. Add REPLICATE_API_TOKEN=<your replicate api key> to .env")

# %%
DATA_FOLDER = '/Users/sangdo/Downloads/replicate_output/'

IMAGE_MODEL = "black-forest-labs/flux-2-pro"
VIDEO_MODEL = "minimax/video-01"


# %%
def _download(url: str, dest_folder: str, default_name: str) -> str:
    import requests

    os.makedirs(dest_folder, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0] or default_name
    dest_path = os.path.join(dest_folder, filename)

    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return dest_path


def _extract_urls(output):
    if isinstance(output, str):
        return [output]
    if isinstance(output, list):
        return [str(item) for item in output]
    # replicate's FileOutput objects expose a .url attribute
    if hasattr(output, "url"):
        return [output.url]
    return [str(output)]


# %%
def generate_image(prompt: str, model: str = IMAGE_MODEL, dest_folder: str = DATA_FOLDER, **extra_args):
    extra_args.setdefault("output_format", "png")
    output = replicate.run(
        model,
        input={
            "prompt": prompt,
            **extra_args,
        },
    )

    urls = _extract_urls(output)
    return [_download(url, dest_folder, f"image_{i}.png") for i, url in enumerate(urls)]


# %%
def generate_video(prompt: str, image_url: str = None, model: str = VIDEO_MODEL, dest_folder: str = DATA_FOLDER, **extra_args):
    input_args = {"prompt": prompt, **extra_args}
    if image_url:
        input_args["start_image"] = image_url

    output = replicate.run(
        model,
        input=input_args,
    )

    urls = _extract_urls(output)
    return _download(urls[0], dest_folder, "video.mp4")


# %%
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an image or video with replicate.com")
    parser.add_argument("mode", choices=["image", "video"], help="What to generate")
    parser.add_argument("prompt", help="Text prompt")
    parser.add_argument("--image-url", help="Source image URL, required for image-to-video models", default=None)
    parser.add_argument("--model", help="Override the replicate model id", default=None)
    args = parser.parse_args()

    if args.mode == "image":
        paths = generate_image(args.prompt, model=args.model or IMAGE_MODEL)
        print("Saved:", paths)
    else:
        path = generate_video(args.prompt, image_url=args.image_url, model=args.model or VIDEO_MODEL)
        print("Saved:", path)
