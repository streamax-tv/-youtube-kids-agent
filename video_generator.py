import os
import re
import subprocess
from pathlib import Path

SCRIPT_FILE = Path("generated_script.txt")
OUT_DIR = Path("output")
VIDEO_FILE = OUT_DIR / "youtube_kids_video.mp4"


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
        prompt = re.search(r"IMAGE\s*/\s*PROMPT STABLE DIFFUSION\s*:\s*\n(.*?)(?=\n\s*VOIX OFF)", block, re.I | re.S)
        if vo:
            scenes.append({"voice": vo.group(1).strip(), "prompt": prompt.group(1).strip() if prompt else ""})
    return scenes


def make_silent_placeholder_scenes(scenes):
    OUT_DIR.mkdir(exist_ok=True)
    # Creates clean scene cards from the generated script. Image generation can be plugged in later.
    for i, scene in enumerate(scenes, 1):
        text = re.sub(r"\*\*", "", scene["voice"])
        text = text.replace("'", "\\'")
        # 7 seconds per scene; last scene may be adjusted by ffmpeg concat.
        vf = f"drawtext=text='{text[:180]}':fontcolor=white:fontsize=34:line_spacing=10:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.55:boxborderw=25"
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x18233a:s=1280x720:r=30", "-t", "7", "-vf", vf, "-pix_fmt", "yuv420p", str(OUT_DIR / f"scene_{i:02d}.mp4")])


def concat_scenes(count):
    concat = OUT_DIR / "concat.txt"
    concat.write_text("\n".join(f"file 'scene_{i:02d}.mp4'" for i in range(1, count + 1)), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(VIDEO_FILE)])


def main():
    if not SCRIPT_FILE.exists():
        raise SystemExit("generated_script.txt introuvable")
    text = SCRIPT_FILE.read_text(encoding="utf-8")
    scenes = extract_scenes(text)
    if not scenes:
        raise SystemExit("Aucune scène trouvée dans le script")
    make_silent_placeholder_scenes(scenes)
    concat_scenes(len(scenes))
    print(f"✅ Vidéo créée: {VIDEO_FILE}")


if __name__ == "__main__":
    main()
