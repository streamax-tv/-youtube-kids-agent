# YouTube Kids Agent

Le pipeline quotidien produit un script avec CrewAI + Gemini.

Les fichiers vidéo temporaires sont créés dans `output/` pendant GitHub Actions.

## YouTube automatique

Le module `youtube_upload.py` utilise OAuth YouTube. Une fois les trois secrets configurés :
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

le workflow peut publier automatiquement la vidéo. Par défaut, la publication est `private` afin de permettre un premier test sécurisé.
