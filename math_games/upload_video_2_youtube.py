# %% [markdown]
# <h2>Upload video to youtube</h2>

# %%
import os

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import random

import shutil
import sys

sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..', 'core')))   #import sibling files

import importlib
import utilities

importlib.reload(utilities)
from utilities import get_first_file, rename_files

import argparse
import json

from dotenv import load_dotenv
load_dotenv(override=True)


# %%
PROJECT_FOLDER = "/Users/sangdo/Documents/Source/Python/python_social_content/"
PROJECT_CORE_FOLDER = f"{PROJECT_FOLDER}core/"

YT_CREDENTIAL_FILEPATH = PROJECT_CORE_FOLDER + "secret_files/martin_yt_client_secret.json" #download from Google console app
YT_SECRET_FILEPATH = PROJECT_CORE_FOLDER + 'secret_files/martin_yt_token.json' #appear after authentication in web (Note this is for 1 channel only)

# %%
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",   #upload file
    "https://www.googleapis.com/auth/youtube.force-ssl" #create comment
]


# %%
DATA_FOLDER = '/Users/sangdo/Downloads/math_games_video/'
VIDEO_FOLDER = f'{DATA_FOLDER}output/'   #contain mp4 files

# %%
COMMENT = os.getenv('COMMENT_CONTENT').replace('\\n', '\n')

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
        # save token again
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

    media = MediaFileUpload(file_path, chunksize=8*1024*1024, resumable=True)

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
def get_random_item(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not data:
        raise ValueError("JSON file is empty")
    
    return random.choice(data)

# Usage
# item = get_random_item(TITLE_FILEPATH)
# print(item['title'])
# print(item['description'])

# %%
def auto_upload_video():
    first_mp4_file, filename = get_first_file(VIDEO_FOLDER, 'mp4')  #order by index
    item = get_random_item(TITLE_FILEPATH)  #get random titles and description
    print('Begin uploading: ' + first_mp4_file)
    new_video_id = upload_video(first_mp4_file, item['title'], item['description'])
    print('===== Done uploading: ' + first_mp4_file)
    #rename the file
    os.rename(first_mp4_file, VIDEO_FOLDER + new_video_id + ".cmt")   #need to comment in this video

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
    video_path, video_id = get_first_file(VIDEO_FOLDER, 'cmt')
    add_comment(video_id, COMMENT)
    os.rename(video_path, VIDEO_FOLDER + video_id + ".fb")   #need to post to FB this video

# %%
# rename_files(VIDEO_FOLDER, 'mp4', 13)
# rename_files('/Users/sangdo/Downloads/math_games_video/img/', 'png', 1)

# %% [markdown]
# <h2>Read the json file that contains titles</h2>

# %%
TITLE_FILEPATH = f'{DATA_FOLDER}math_titles_500.json'

def get_all_titles(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [item['title'] for item in data]

# Usage
# titles = get_all_titles(TITLE_FILEPATH)
# for title in titles:
#     print(title)

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



