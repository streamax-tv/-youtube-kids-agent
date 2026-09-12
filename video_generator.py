import asyncio
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_FILE = Path("generated_script.txt")
OUT_DIR = Path("output")
VIDEO_FILE = OUT_DIR / "youtube_kids_video.mp4"
VOICE = "fr-FR-DeniseNeural"
SCENE_DURATION = 7.5
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "").strip()
MEDIA_MODE = os.getenv("MEDIA_MODE", "image").strip().lower()  # image or video
IMAGE_MODEL = os.getenv("POLLINATIONS_IMAGE_MODEL", "flux")
VIDEO_MODEL = os.getenv("POLLINATIONS_VIDEO_MODEL", "veo")

BACKGROUNDS = ["0x173B57", "0x245B6B", "0x3D4F7A", "0x6A4C93", "0x2E6F59", "0x4B5D8A"]

CHARACTER_BIBLE = (
    "Original recurring characters for a children's educational series: Kibo, a small funny articulated wooden robot "
    "made of rounded warm wood blocks, big friendly eyes, simple child-safe design; Pipistrelle, a tiny cute purple "
    "felt bat with oversized ears and soft fabric texture. Keep their appearance, colors, proportions and personality "
    "consistent across every scene. Original 3D animated feature look, handcrafted toy-like materials, expressive faces, "
    "cinematic soft lighting, colorful whimsical environment, polished high-end children's animation, no logos, no text, "
    "no existing franchise characters, no imitation of a named studio."
)


def run(cmd):
    print("$", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)


def extract_scenes(text):
    scenes = []
    blocks = re.split(r"(?=SCÈNE\s+\d+)", text, flags=re.I)
    for block in blocks:
        if not re.search(r"SCÈNE\s+\d+", block, re.I):
            continue
        vo = re.search(r"VOIX OFF\s*:\s*\n(.*?)(?=\n\s*---|\n\s*SCÈNE|\Z)", block, re.I | re.S)
        prompt = re.search(r"IMAGE\s*/\s*PROMPT[^:]*:\s*\n?\[(.*?)\]", block, re.I | re.S)
        if vo:
            voice = re.sub(r"\*\*(.*?)\*\*", r"\1", vo.group(1).strip())
            image_prompt = prompt.group(1).strip() if prompt else "A colorful educational children's scene with Kibo and Pipistrelle."
            scenes.append({"voice": voice, "prompt": image_prompt})
    return scenes


async def make_audio(text, path):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(path))


def probe_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def atempo_chain(speed):
    filters = []
    while speed > 2.0:
        filters.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        filters.append("atempo=0.5")
        speed /= 0.5
    filters.append(f"atempo={speed:.6f}")
    return ",".join(filters)


def auth_headers():
    return {"Authorization": f"Bearer {POLLINATIONS_API_KEY}", "User-Agent": "youtube-kids-agent/1.0"}


def download_ai_image(prompt, index):
    if not POLLINATIONS_API_KEY:
        return None
    final_prompt = f"{CHARACTER_BIBLE} Scene {index}: {prompt}. 16:9 composition, strong visual storytelling, no written words."
    encoded = urllib.parse.quote(final_prompt, safe="")
    url = f"https://gen.pollinations.ai/image/{encoded}?model={urllib.parse.quote(IMAGE_MODEL)}&width=1280&height=720&nologo=true"
    target = OUT_DIR / f"ai_scene_{index:02d}.jpg"
    request = urllib.request.Request(url, headers=auth_headers())
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            target.write_bytes(response.read())
        if target.stat().st_size < 10000:
            target.unlink(missing_ok=True)
            return None
        print(f"🖼️ AI image {index}: {target}")
        return target
    except Exception as exc:
        print(f"⚠️ AI image {index} unavailable: {exc}")
        target.unlink(missing_ok=True)
        return None


def download_ai_video(prompt, index):
    if not POLLINATIONS_API_KEY:
        return None
    final_prompt = f"{CHARACTER_BIBLE} Scene {index}: {prompt}. Natural child-friendly motion, expressive action, cinematic camera movement, polished animation, no text."
    encoded = urllib.parse.quote(final_prompt, safe="")
    url = f"https://gen.pollinations.ai/video/{encoded}?model={urllib.parse.quote(VIDEO_MODEL)}&duration=7"
    target = OUT_DIR / f"ai_scene_{index:02d}.mp4"
    request = urllib.request.Request(url, headers=auth_headers())
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            target.write_bytes(response.read())
        if target.stat().st_size < 100000:
            target.unlink(missing_ok=True)
            return None
        print(f"🎥 AI video {index}: {target}")
        return target
    except Exception as exc:
        print(f"⚠️ AI video {index} unavailable: {exc}")
        target.unlink(missing_ok=True)
        return None


def make_animated_scene(image_path, audio, index):
    scene = OUT_DIR / f"scene_{index:02d}.mp4"
    audio_duration = probe_duration(audio)
    speed = max(1.0, audio_duration / SCENE_DURATION)
    audio_filter = atempo_chain(speed) if speed > 1.01 else "anull"
    # Gentle cinematic Ken Burns movement keeps still AI art lively without uncanny motion.
    zoom = "min(zoom+0.0008,1.10)" if index % 2 else "max(zoom-0.0008,1.00)"
    x = "iw/2-(iw/zoom/2)" if index % 2 else "0"
    vf = (
        f"scale=1400:-2,zoompan=z='{zoom}':x='{x}':y='ih/2-(ih/zoom/2)':d=225:s=1280x720:fps=30,"
        "fade=t=in:st=0:d=0.35,fade=t=out:st=7.05:d=0.35"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image_path), "-i", str(audio),
        "-filter_complex", f"[1:a]{audio_filter}[a]", "-map", "0:v:0", "-map", "[a]",
        "-t", str(SCENE_DURATION), "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "19", "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(scene),
    ])


def make_fallback_scene(text, audio, index):
    scene = OUT_DIR / f"scene_{index:02d}.mp4"
    text_file = OUT_DIR / f"caption_{index:02d}.txt"
    text_file.write_text(text[:420], encoding="utf-8")
    audio_duration = probe_duration(audio)
    speed = max(1.0, audio_duration / SCENE_DURATION)
    audio_filter = atempo_chain(speed) if speed > 1.01 else "anull"
    bg = BACKGROUNDS[(index - 1) % len(BACKGROUNDS)]
    filter_graph = (
        "drawbox=x=55:y=55:w=1170:h=610:color=white@0.10:t=5,"
        "drawbox=x=85:y=85:w=1110:h=550:color=black@0.12:t=2,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='KIBO & PIPISTRELLE  •  {index}/6':fontcolor=white@0.92:fontsize=28:x=80:y=38,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"textfile='{text_file}':fontcolor=white:fontsize=38:line_spacing=14:"
        "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.42:boxborderw=34"
    )
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={bg}:s=1280x720:r=30", "-i", str(audio),
        "-filter_complex", f"[1:a]{audio_filter}[a]", "-map", "0:v:0", "-map", "[a]", "-t", str(SCENE_DURATION),
        "-vf", filter_graph, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-c:a", "aac",
        "-b:a", "128k", "-ar", "48000", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(scene),
    ])


def concat_scenes(count):
    concat = OUT_DIR / "concat.txt"
    concat.write_text("\n".join(f"file 'scene_{i:02d}.mp4'" for i in range(1, count + 1)), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(VIDEO_FILE)])


def main():
    if not SCRIPT_FILE.exists():
        raise SystemExit("generated_script.txt introuvable")
    scenes = extract_scenes(SCRIPT_FILE.read_text(encoding="utf-8"))
    if not scenes:
        raise SystemExit("Aucune scène trouvée dans le script")
    if len(scenes) != 6:
        print(f"⚠️ {len(scenes)} scènes détectées; durée cible {len(scenes) * SCENE_DURATION:.1f}s.")
    OUT_DIR.mkdir(exist_ok=True)
    for pattern in ("scene_*.mp4", "voice_*.mp3", "caption_*.txt", "ai_scene_*.jpg", "ai_scene_*.mp4"):
        for old in OUT_DIR.glob(pattern):
            old.unlink()

    for i, scene_data in enumerate(scenes, 1):
        audio = OUT_DIR / f"voice_{i:02d}.mp3"
        asyncio.run(make_audio(scene_data["voice"], audio))
        ai_media = download_ai_video(scene_data["prompt"], i) if MEDIA_MODE == "video" else download_ai_image(scene_data["prompt"], i)
        if ai_media and ai_media.suffix.lower() == ".mp4":
            # Normalize AI clip length/codec and pair it with the generated French voice.
            scene = OUT_DIR / f"scene_{i:02d}.mp4"
            audio_duration = probe_duration(audio)
            speed = max(1.0, audio_duration / SCENE_DURATION)
            audio_filter = atempo_chain(speed) if speed > 1.01 else "anull"
            run([
                "ffmpeg", "-y", "-i", str(ai_media), "-i", str(audio),
                "-filter_complex", f"[1:a]{audio_filter}[a]", "-map", "0:v:0", "-map", "[a]",
                "-t", str(SCENE_DURATION), "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-c:a", "aac", "-b:a", "160k",
                "-ar", "48000", "-movflags", "+faststart", str(scene),
            ])
        elif ai_media:
            make_animated_scene(ai_media, audio, i)
        else:
            make_fallback_scene(scene_data["voice"], audio, i)

    concat_scenes(len(scenes))
    final_duration = probe_duration(VIDEO_FILE)
    print(f"✅ Vidéo créée: {VIDEO_FILE} ({final_duration:.1f}s) | mode={MEDIA_MODE} | AI={'oui' if POLLINATIONS_API_KEY else 'non'}")


if __name__ == "__main__":
    main()
