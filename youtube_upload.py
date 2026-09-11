import os
import re
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VIDEO = Path("output/youtube_kids_video.mp4")
SCRIPT = Path("generated_script.txt")


def script_metadata():
    title = "Comptine éducative pour enfants 🌈"
    theme = ""
    if SCRIPT.exists():
        text = SCRIPT.read_text(encoding="utf-8")
        match = re.search(r"^TITRE\s*:\s*(.+)$", text, re.I | re.M)
        if match:
            title = match.group(1).strip()
        match = re.search(r"^THÈME\s*:\s*(.+)$", text, re.I | re.M)
        if match:
            theme = match.group(1).strip()
    description = (
        "Une nouvelle aventure éducative originale pour les enfants, créée automatiquement.\n\n"
        + (f"Thème : {theme}\n\n" if theme else "")
        + "#enfants #éducation #comptine #apprentissage #français"
    )
    return title[:100], description[:5000]


def main():
    if not VIDEO.exists():
        raise SystemExit("Vidéo introuvable: output/youtube_kids_video.mp4")

    token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    if not all([token, client_id, client_secret]):
        print("ℹ️ YouTube OAuth non configuré. La vidéo reste disponible comme Artifact.")
        return

    creds = Credentials(
        token=None,
        refresh_token=token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )

    youtube = build("youtube", "v3", credentials=creds)
    default_title, default_description = script_metadata()
    title = os.environ.get("YOUTUBE_TITLE", default_title)[:100]
    description = os.environ.get("YOUTUBE_DESCRIPTION", default_description)
    privacy = os.environ.get("YOUTUBE_PRIVACY", "private")

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "27",
                "defaultLanguage": "fr",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": True,
            },
        },
        media_body=MediaFileUpload(str(VIDEO), mimetype="video/mp4", resumable=True),
    )
    response = request.execute()
    video_id = response.get("id")
    print(f"✅ Vidéo envoyée sur YouTube: {video_id}")
    print(f"📺 https://www.youtube.com/watch?v={video_id}")


if __name__ == "__main__":
    main()
