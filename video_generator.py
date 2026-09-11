import asyncio
import re
import subprocess
from pathlib import Path

SCRIPT_FILE = Path("generated_script.txt")
OUT_DIR = Path("output")
VIDEO_FILE = OUT_DIR / "youtube_kids_video.mp4"
VOICE = "fr-FR-DeniseNeural"
SCENE_DURATION = 7.5

BACKGROUNDS = [
    "0x173B57",
    "0x245B6B",
    "0x3D4F7A",
    "0x6A4C93",
    "0x2E6F59",
    "0x4B5D8A",
]


def run(cmd):
    print("$", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)


def extract_scenes(text):
    scenes = []
    blocks = re.split(r"(?=SCÈNE\s+\d+)", text, flags=re.I)
    for block in blocks:
        if not re.search(r"SCÈNE\s+\d+", block, re.I):
            continue
        vo = re.search(
            r"VOIX OFF\s*:\s*\n(.*?)(?=\n\s*---|\n\s*SCÈNE|\Z)",
            block,
            re.I | re.S,
        )
        if vo:
            voice = re.sub(r"\*\*(.*?)\*\*", r"\1", vo.group(1).strip())
            scenes.append(voice)
    return scenes


async def make_audio(text, path):
    import edge_tts

    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(str(path))


def wrap_text(text, width=48):
    words = text.split()
    lines = []
    current = []
    length = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and length + extra > width:
            lines.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += extra
    if current:
        lines.append(" ".join(current))
    return "\n".join(lines)


def probe_duration(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def atempo_chain(speed):
    # FFmpeg atempo accepts 0.5..2.0 per filter. Split larger speedups safely.
    filters = []
    while speed > 2.0:
        filters.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        filters.append("atempo=0.5")
        speed /= 0.5
    filters.append(f"atempo={speed:.6f}")
    return ",".join(filters)


def make_scene(text, index):
    audio = OUT_DIR / f"voice_{index:02d}.mp3"
    scene = OUT_DIR / f"scene_{index:02d}.mp4"
    text_file = OUT_DIR / f"caption_{index:02d}.txt"

    asyncio.run(make_audio(text, audio))
    text_file.write_text(wrap_text(text[:420]), encoding="utf-8")

    audio_duration = probe_duration(audio)
    # Keep the final video at exactly 6 x 7.5 s = 45 s.
    # If TTS is longer, speed it up rather than cutting words.
    speed = max(1.0, audio_duration / SCENE_DURATION)
    audio_filter = atempo_chain(speed) if speed > 1.01 else "anull"

    bg = BACKGROUNDS[(index - 1) % len(BACKGROUNDS)]
    filter_graph = (
        "drawbox=x=55:y=55:w=1170:h=610:color=white@0.10:t=5,"
        "drawbox=x=85:y=85:w=1110:h=550:color=black@0.12:t=2,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='DÉCOUVRE ET BOUGE  •  {index}/6':fontcolor=white@0.92:fontsize=28:"
        "x=80:y=38,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"textfile='{text_file}':fontcolor=white:fontsize=38:line_spacing=14:"
        "x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.42:boxborderw=34"
    )

    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={bg}:s=1280x720:r=30",
        "-i", str(audio),
        "-filter_complex", f"[1:a]{audio_filter}[a]",
        "-map", "0:v:0",
        "-map", "[a]",
        "-t", str(SCENE_DURATION),
        "-vf", filter_graph,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "48000",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(scene),
    ])


def concat_scenes(count):
    concat = OUT_DIR / "concat.txt"
    concat.write_text(
        "\n".join(f"file 'scene_{i:02d}.mp4'" for i in range(1, count + 1)),
        encoding="utf-8",
    )
    run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat),
        "-c", "copy",
        "-movflags", "+faststart",
        str(VIDEO_FILE),
    ])


def main():
    if not SCRIPT_FILE.exists():
        raise SystemExit("generated_script.txt introuvable")

    scenes = extract_scenes(SCRIPT_FILE.read_text(encoding="utf-8"))
    if not scenes:
        raise SystemExit("Aucune scène trouvée dans le script")

    # The script format targets six scenes / 45 seconds.
    if len(scenes) != 6:
        print(f"⚠️ {len(scenes)} scènes détectées; la durée totale sera {len(scenes) * SCENE_DURATION:.1f}s.")

    OUT_DIR.mkdir(exist_ok=True)
    for pattern in ("scene_*.mp4", "voice_*.mp3", "caption_*.txt"):
        for old in OUT_DIR.glob(pattern):
            old.unlink()

    for i, text in enumerate(scenes, 1):
        make_scene(text, i)

    concat_scenes(len(scenes))
    final_duration = probe_duration(VIDEO_FILE)
    print(f"✅ Vidéo avec voix française créée: {VIDEO_FILE} ({final_duration:.1f}s)")


if __name__ == "__main__":
    main()
