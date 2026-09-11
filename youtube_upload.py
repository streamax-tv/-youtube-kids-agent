import os
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

VIDEO = Path("output/youtube_kids_video.mp4")


def main():
    if not VIDEO.exists():
        raise SystemExit("Vidéo introuvable: output/youtube_kids_video.mp4")
    token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    if not all([token, client_id, client_secret]):
        print("ℹ️ YouTube OAuth non configuré. La vidéo reste disponible dans output/.")
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
    title = os.environ.get("YOUTUBE_TITLE", "Comptine éducative pour enfants 🌈")[:100]
    description = os.environ.get("YOUTUBE_DESCRIPTION", "Une nouvelle aventure éducative pour les enfants !")
    request = youtube.videos().insert(
        part="snippet,status",
        body={"snippet": {"title": title, "description": description, "categoryId": "27", "defaultLanguage": "fr"},
              "status": {"privacyStatus": os.environ.get("YOUTUBE_PRIVACY", "private"), "selfDeclaredMadeForKids": True}},
        media_body=MediaFileUpload(str(VIDEO), mimetype="video/mp4", resumable=True),
    )
    response = request.execute()
    print("✅ Vidéo envoyée sur YouTube:", response.get("id"))


if __name__ == "__main__":
    main()
