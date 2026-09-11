import asyncio
import re
import subprocess
from pathlib import Path

SCRIPT_FILE = Path("generated_script.txt")
OUT_DIR = Path("output")
VIDEO_FILE = OUT_DIR / "youtube_kids_video.mp4"
VOICE = "fr-FR-DeniseNeural"


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
        if vo:
            voice = re.sub(r"\*\*(.*?)\*\*", r"\1", vo.group(1).strip())
            scenes.append(voice)
    return scenes


async def make_audio(text, path):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(path))


def make_scene(text, index):
    audio = OUT_DIR / f"voice_{index:02d}.mp3"
    scene = OUT_DIR / f"scene_{index:02d}.mp4"
    asyncio.run(make_audio(text, audio))

    # Escaping for FFmpeg drawtext.
    safe = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")
    vf = (
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"text='{safe[:220]}':fontcolor=white:fontsize=34:line_spacing=10:"
        "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.55:boxborderw=28"
    )
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x18233a:s=1280x720:r=30",
        "-i", str(audio), "-shortest", "-vf", vf, "-c:v", "libx264", "-c:a", "aac",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(scene)
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
    OUT_DIR.mkdir(exist_ok=True)
    for i, text in enumerate(scenes, 1):
        make_scene(text, i)
    concat_scenes(len(scenes))
    print(f"✅ Vidéo avec voix française créée: {VIDEO_FILE}")


if __name__ == "__main__":
    main()
