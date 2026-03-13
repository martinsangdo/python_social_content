# %% [markdown]
# <h2>Upload video to youtube</h2>

# %%
import os

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import importlib
import utilities
import shutil
import sys

importlib.reload(utilities)
from utilities import get_first_file, rename_files

import argparse


# %%
PROJECT_CORE_FOLDER = "/Users/sangdo/Documents/Source/Python/python_social_content/core/"

# %%
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",   #upload file
    "https://www.googleapis.com/auth/youtube.force-ssl" #create comment
]


# %%
VIDEO_FOLDER = '/Users/sangdo/Downloads/math_games_video/output/'   #contain mp4 files
UPLOADED_VIDEO_FOLDER = '/Users/sangdo/Downloads/math_games_video/output/yt_uploaded/'   #contain mp4 files

# %%
YT_CREDENTIAL_FILEPATH = PROJECT_CORE_FOLDER + "secret_files/martin_yt_client_secret.json" #download from Google console app
YT_SECRET_FILEPATH = PROJECT_CORE_FOLDER + 'secret_files/martin_yt_token.json' #appear after authentication in web (Note this is for 1 channel only)

# %%
TITLE_PREFIX = 'Math games for your kids at the spare time - Puzzle '
DESCRIPTION = """
Download more than 300 Math Games as a printable PDF file for your kids here: 

https://sangdomartin.gumroad.com/l/mathgames

We introduce a range of various games:
Addition matrix
Hidden gems
Word search
Crossword numbers
Balance game
Find lines
Triangle sum
Balance fruit
Object coordination
Spy game
Detect shape
Bee house
"""
COMMENT = """
Download more than 300 Math Games as a printable PDF file for your kids here: 

https://sangdomartin.gumroad.com/l/mathgames
"""

# %%
#authorize to save permanent token
def get_authenticated_service():
    creds = None
    # load saved token
    if os.path.exists(YT_SECRET_FILEPATH):
        print("Using saved Youtube token")
        creds = Credentials.from_authorized_user_file(YT_SECRET_FILEPATH, SCOPES)

    # if no valid credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                YT_CREDENTIAL_FILEPATH,
                SCOPES
            )
            flow.oauth2session.params["access_type"] = "offline"
            creds = flow.run_local_server(port=0)
        # save token
        with open(YT_SECRET_FILEPATH, "w") as token:
            token.write(creds.to_json())

    youtube = build("youtube", "v3", credentials=creds)
    return youtube

youtube = get_authenticated_service() #permanent token is saved. Note: login with developer account (Tester type)

# %%
def upload_video(file_path, title, description):
    request_body = {
        "snippet": {
            "title": title,
            "description": description
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    media = MediaFileUpload(file_path, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = None

    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Uploading {int(status.progress() * 100)}%")

    print("Upload complete")
    print("Video ID:", response["id"])
    return response["id"]

# %%
def auto_upload_video():
    first_mp4_file, filename = get_first_file(VIDEO_FOLDER, 'mp4')
    print('Begin uploading: ' + first_mp4_file)
    new_video_id = upload_video(first_mp4_file, TITLE_PREFIX + filename, DESCRIPTION)
    print('===== Done uploading: ' + first_mp4_file)
    shutil.move(first_mp4_file, os.path.join(UPLOADED_VIDEO_FOLDER, new_video_id + '.mp4'))  #move that file to another folder after uploading

# %%
def add_comment(video_id, comment_text):
    request = youtube.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": comment_text
                    }
                }
            }
        }
    )

    response = request.execute()
    print("Comment posted")
    return response
#
def auto_add_comment():
    #find the first file in path
    video_path, video_id = get_first_file(UPLOADED_VIDEO_FOLDER, 'mp4')
    add_comment(video_id, COMMENT)
    os.remove(video_path)

# %%
#testing in jupyter
# sys.argv = ['script.py', '-type', 'comment']
#load parameters
parser = argparse.ArgumentParser()
parser.add_argument('-type', type=str, default=None, help='Action type: upload_video or comment')

args,_ = parser.parse_known_args()
if args.type is None:
    print('Type not found')
    raise SystemExit
action_type = args.type
print('action type:', action_type)
if action_type == 'upload_video':
    auto_upload_video()
elif action_type == 'comment':
    auto_add_comment()


# %%
# rename_files(VIDEO_FOLDER, 'mp4', 13)


