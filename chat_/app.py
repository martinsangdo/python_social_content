# %% [markdown]
# <h2>Generate an image from a text description and upload it to Supabase storage</h2>

import os
import sys
import uuid
import mimetypes

import streamlit as st
import replicate
from supabase import create_client

# Works in both .py files and Jupyter notebooks
try:
    base_path = os.path.dirname(__file__)  # works in .py files
except NameError:
    base_path = os.getcwd()                # fallback for Jupyter notebooks

core_path = os.path.abspath(os.path.join(base_path, '..', 'core'))
sys.path.append(core_path)

from dotenv import load_dotenv
load_dotenv(override=True)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL / SUPABASE_KEY are not set. "
        "Add SUPABASE_URL=<your project url> and SUPABASE_KEY=<your service role or anon key> to .env"
    )

if not os.environ.get("REPLICATE_API_TOKEN"):
    raise RuntimeError("REPLICATE_API_TOKEN is not set. Add REPLICATE_API_TOKEN=<your replicate api key> to .env")

BUCKET_NAME = "media"
IMAGE_MODEL = "black-forest-labs/flux-2-pro"
DATA_FOLDER = os.path.join(base_path, "generated_images")


# --- image generation (media/replicate_test.py logic) ---

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


# --- upload to Supabase (media/upload_test.py logic) ---

def upload_file(file_path: str, bucket_name: str = BUCKET_NAME, dest_path: str = None) -> str:
    """Upload an image/video file to Supabase storage and return its public URL."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)

    dest_path = dest_path or os.path.basename(file_path)
    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    with open(file_path, "rb") as f:
        client.storage.from_(bucket_name).upload(
            path=dest_path,
            file=f,
            file_options={"content-type": content_type, "upsert": "true"},
        )

    return client.storage.from_(bucket_name).get_public_url(dest_path)


# --- Streamlit UI ---

st.set_page_config(page_title="Image Generator", page_icon="🖼️")
st.title("Generate & Upload an Image")

prompt = st.text_area("Describe the image you want to create", height=120,
                       placeholder="e.g. a cat riding a skateboard on the moon")
bucket = st.text_input("Supabase bucket", value=BUCKET_NAME)

if st.button("Generate & Upload", type="primary", disabled=not prompt.strip()):
    with st.spinner("Generating image..."):
        paths = generate_image(prompt)
        local_path = paths[0]

    with st.spinner("Uploading to Supabase..."):
        dest_path = f"{uuid.uuid4().hex}{os.path.splitext(local_path)[1]}"
        public_url = upload_file(local_path, bucket_name=bucket, dest_path=dest_path)

    st.success("Done!")
    st.image(local_path, caption=prompt)
    st.write("Public URL:", public_url)
