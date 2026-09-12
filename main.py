# -*- coding: utf-8 -*-
"""Agent quotidien YouTube Kids : tendance -> script original."""
import os
from typing import Dict, List
from googleapiclient.discovery import build
from crewai import Agent, Crew, LLM, Process, Task

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
MODEL_NAME = "gemini-3.6-flash"

llm = LLM(model=f"gemini/{MODEL_NAME}", api_key=GEMINI_API_KEY)


def get_top_youtube_videos(keyword: str = "comptines éducatives enfants", max_results: int = 5) -> List[Dict[str, str]]:
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    response = youtube.search().list(
        part="snippet", q=keyword, type="video", order="viewCount",
        maxResults=max_results, relevanceLanguage="fr", safeSearch="strict"
    ).execute()
    video_ids = [item["id"]["videoId"] for item in response.get("items", []) if item.get("id", {}).get("videoId")]
    if not video_ids:
        return []
    details = youtube.videos().list(part="snippet,statistics", id=",".join(video_ids)).execute()
    videos = []
    for video in details.get("items", []):
        snippet, stats = video.get("snippet", {}), video.get("statistics", {})
        videos.append({
            "title": snippet.get("title", ""), "channel": snippet.get("channelTitle", ""),
            "published_at": snippet.get("publishedAt", ""), "views": stats.get("viewCount", "0"),
            "video_id": video["id"], "url": f"https://www.youtube.com/watch?v={video['id']}"
        })
    videos.sort(key=lambda item: int(item["views"] or 0), reverse=True)
    return videos[:max_results]


detective = Agent(
    role="Détective des tendances YouTube Kids",
    goal="Analyser les vidéos populaires et identifier le thème majeur, le concept éducatif et les mécanismes de popularité.",
    backstory="Tu es un analyste spécialisé dans les contenus vidéo pour enfants. Tu détectes les tendances sans copier les œuvres existantes.",
    llm=llm, verbose=True,
)

scenariste = Agent(
    role="Scénariste de vidéos éducatives pour enfants",
    goal="Créer un script de 45 secondes avec une identité visuelle originale et cohérente.",
    backstory="Tu écris des histoires courtes, joyeuses, simples et éducatives pour les enfants. Tu crées toujours du contenu original.",
    llm=llm, verbose=True,
)


def main() -> None:
    print("🔎 Recherche YouTube...")
    videos = get_top_youtube_videos()
    if not videos:
        raise RuntimeError("Aucune vidéo YouTube trouvée.")
    videos_text = "\n\n".join(
        f"Titre : {v['title']}\nChaîne : {v['channel']}\nVues : {v['views']}\nDate : {v['published_at']}\nURL : {v['url']}"
        for v in videos
    )

    detective_task = Task(
        description=f"""Analyse ces 5 vidéos YouTube Kids :

{videos_text}

Identifie : 1. Le thème majeur. 2. Le concept éducatif dominant. 3. Les sujets récurrents.
4. Les éléments de popularité. 5. Les caractéristiques visuelles/narratives utiles.
6. Une piste de concept totalement originale.

Ne copie aucun personnage, titre, parole ou scène existante.""",
        expected_output="Une analyse structurée suivie d'une tendance majeure claire.", agent=detective,
    )

    writer_task = Task(
        description="""À partir de l'analyse du Détective, écris un script ORIGINAL d'environ 45 secondes pour une vidéo YouTube Kids en français.

Format obligatoire :
TITRE :
...
THÈME :
...
DURÉE :
45 secondes
PERSONNAGES :
...

SCÈNE 1 — 0:00 à 0:07
IMAGE / PROMPT STABLE DIFFUSION :
[Prompt en anglais : sujet, décor, action, caméra, éclairage, matériaux et style visuel original]
VOIX OFF :
[français]

SCÈNE 2 — 0:07 à 0:14
IMAGE / PROMPT STABLE DIFFUSION :
...
VOIX OFF :
...

SCÈNE 3 — 0:14 à 0:21
IMAGE / PROMPT STABLE DIFFUSION :
...
VOIX OFF :
...

SCÈNE 4 — 0:21 à 0:30
IMAGE / PROMPT STABLE DIFFUSION :
...
VOIX OFF :
...

SCÈNE 5 — 0:30 à 0:38
IMAGE / PROMPT STABLE DIFFUSION :
...
VOIX OFF :
...

SCÈNE 6 — 0:38 à 0:45
IMAGE / PROMPT STABLE DIFFUSION :
...
VOIX OFF :
...

CONCLUSION :
[ce que l'enfant apprend]

Règles visuelles importantes : définis une identité visuelle originale et réutilisable. Décris précisément les mêmes personnages
à chaque scène pour conserver leur apparence. Utilise un rendu d'animation 3D original, haut de gamme, coloré et chaleureux,
avec matériaux de jouet/artisanat, expressions lisibles, profondeur de champ douce et éclairage cinématographique.
N'utilise le nom d'aucun studio, réalisateur, franchise ou artiste comme référence de style. Aucun texte dans les images.

Contraintes : français simple, ton joyeux et éducatif, contenu adapté aux enfants, concept entièrement original,
aucun personnage de franchise connue, aucun texte ou scène copié, prompts en anglais et voix off en français.""",
        expected_output="Un script complet, original et structuré de 45 secondes.", agent=scenariste, context=[detective_task],
    )

    crew = Crew(agents=[detective, scenariste], tasks=[detective_task, writer_task], process=Process.sequential, verbose=True)
    print("🤖 Lancement de CrewAI + Gemini...")
    result = crew.kickoff()
    with open("generated_script.txt", "w", encoding="utf-8") as file:
        file.write(str(result) + "\n")
    print("✅ generated_script.txt a été généré.")


if __name__ == "__main__":
    main()
