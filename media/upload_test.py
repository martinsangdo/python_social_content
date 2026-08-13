# %% [markdown]
# <h2>Upload an image/video to Supabase storage</h2>

# %%
import os
import sys
import argparse
import mimetypes

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

# %%
BUCKET_NAME = "my_bucket_1"


# %%
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


# %%
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload an image/video to Supabase storage")
    parser.add_argument("file_path", help="Path to the local image/video file")
    parser.add_argument("--bucket", help="Supabase storage bucket name", default=BUCKET_NAME)
    parser.add_argument("--dest-path", help="Destination path/filename in the bucket", default=None)
    args = parser.parse_args()

    url = upload_file(args.file_path, bucket_name=args.bucket, dest_path=args.dest_path)
    print("Public URL:", url)

#python3.10 upload_test.py /Users/sangdo/Downloads/replicate_output/tmpbyehhxri.png --bucket my_bucket_1