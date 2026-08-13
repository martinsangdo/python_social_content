# %% [markdown]
# <h2>Edit an uploaded image from a text description and upload the result to Supabase storage</h2>

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

BUCKET_NAME = "my_bucket_1"
IMAGE_EDIT_MODEL = "black-forest-labs/flux-kontext-pro"
UPLOAD_FOLDER = os.path.join(base_path, "uploaded_images")
EDITED_FOLDER = os.path.join(base_path, "edited_images")


# --- image editing (chat_/app.py generate_image logic, adapted for image-to-image) ---

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


def edit_image(prompt: str, input_image_path: str, model: str = IMAGE_EDIT_MODEL,
               dest_folder: str = EDITED_FOLDER, **extra_args):
    extra_args.setdefault("output_format", "png")
    with open(input_image_path, "rb") as image_file:
        output = replicate.run(
            model,
            input={
                "prompt": prompt,
                "input_image": image_file,
                **extra_args,
            },
        )

    urls = _extract_urls(output)
    return [_download(url, dest_folder, f"edited_{i}.png") for i, url in enumerate(urls)]


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

st.set_page_config(page_title="Image Editor", page_icon="🎨")
st.title("Edit & Upload an Image")

uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg", "webp"])
prompt = st.text_area("Describe how you want to edit this image", height=120,
                       placeholder="e.g. make the sky sunset orange and add birds flying")
bucket = st.text_input("Supabase bucket", value=BUCKET_NAME)

if uploaded_file is not None:
    st.image(uploaded_file, caption="Original image")

can_submit = uploaded_file is not None and bool(prompt.strip())

if st.button("Edit & Upload", type="primary", disabled=not can_submit):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    upload_ext = os.path.splitext(uploaded_file.name)[1] or ".png"
    local_input_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}{upload_ext}")
    with open(local_input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with st.spinner("Editing image..."):
        paths = edit_image(prompt, local_input_path)
        local_edited_path = paths[0]

    with st.spinner("Uploading original and edited images to Supabase..."):
        original_dest_path = f"{uuid.uuid4().hex}{upload_ext}"
        original_public_url = upload_file(local_input_path, bucket_name=bucket, dest_path=original_dest_path)

        edited_dest_path = f"{uuid.uuid4().hex}{os.path.splitext(local_edited_path)[1]}"
        edited_public_url = upload_file(local_edited_path, bucket_name=bucket, dest_path=edited_dest_path)

    st.success("Done!")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Original")
        st.image(local_input_path)
        st.write("Public URL:", original_public_url)
    with col2:
        st.subheader("Edited")
        st.image(local_edited_path, caption=prompt)
        st.write("Public URL:", edited_public_url)
