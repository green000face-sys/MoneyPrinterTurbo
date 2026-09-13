#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

BASE_URL = os.getenv("OFOX_BASE_URL", "https://api.ofox.ai/v1").rstrip("/")
MODEL = os.getenv("OFOX_VIDEO_MODEL", "bytedance/seedance-2.0-mini")
RESOLUTION = os.getenv("OFOX_RESOLUTION", "720p")
PROVIDER = os.getenv("OFOX_PROVIDER", "byteplus")
POLL_SECONDS = float(os.getenv("OFOX_POLL_SECONDS", "5"))

STYLE = (
    "High-quality warm 3D animated kids cartoon. Vertical 9:16. "
    "Keep Jasmine and Sam visually identical to the supplied character reference images. "
    "Sam: playful, mischievous, energetic. Jasmine: calm, smart, observant. "
    "Strong facial reactions, expressive eyes, natural body language, polished soft lighting. "
    "Start immediately with the characters and action. No establishing shot. "
    "Absolutely no dialogue, no narration, no spoken words, no lip-sync, no mumbling, "
    "no babbling, no gibberish, no fake language, no subtitles, no captions, no logos, no watermark. "
    "No generated speech audio. Family-friendly gentle physical comedy."
)

SCENARIOS = {
    "4": {
        "title": "Sam's Ice Cream Trouble",
        "clips": [
            (12, "Sam stares at a colorful bowl of ice cream with huge excited eyes and a mischievous grin. Jasmine notices him and gives a suspicious side-eye. Sam looks left and right and slowly reaches for the bowl while Jasmine raises one eyebrow and shakes her head."),
            (12, "Sam quickly reaches for the ice cream. The spoon flips a small scoop into the air. Jasmine and Sam track it with huge shocked eyes. The scoop lands gently on Sam's nose. He freezes and crosses his eyes trying to see it while Jasmine giggles."),
            (11, "Sam makes funny embarrassed faces and tries to reach the ice cream on his nose. Jasmine wipes it away with a napkin. A tiny drop lands on Jasmine's nose. She freezes, gives Sam a dramatic look, then both laugh together."),
        ],
    },
    "5": {
        "title": "The Dancing Shoes",
        "clips": [
            (12, "Sam notices a funny pair of shiny shoes, eyes widening with a mischievous smile. He puts them on. The shoes suddenly move his feet by themselves. Sam changes from proud to confused while Jasmine starts giggling."),
            (12, "The shoes make Sam dance faster. He wiggles, spins, slides and bounces with exaggerated shocked facial expressions. Jasmine laughs and notices a small OFF button on one shoe."),
            (11, "Jasmine presses the OFF button. Sam freezes in a ridiculous dance pose and slowly looks at her. Both laugh. One shoe makes one final tiny hop. Sam jumps in surprise, removes both shoes and holds them far away while Jasmine laughs harder."),
        ],
    },
    "6": {
        "title": "Sam Becomes Grandpa",
        "clips": [
            (12, "Sam is already wearing Grandpa's oversized glasses and hat, making a funny serious face and standing like Grandpa. Jasmine sees him, freezes in surprise, then giggles as Sam starts an exaggerated slow Grandpa walk."),
            (12, "Grandpa enters and sees Sam copying him. Grandpa's eyes widen and eyebrows rise dramatically. Sam freezes, then continues the imitation. The glasses slide down Sam's nose and the hat turns sideways. Jasmine and Grandpa laugh."),
            (11, "Grandpa gently fixes Sam's glasses and hat, then stands beside Sam and copies Sam's silly pose. Sam realizes Grandpa is now copying him. Jasmine claps and all three laugh together with warm family expressions."),
        ],
    },
    "7": {
        "title": "Grandma's Cake Surprise",
        "clips": [
            (12, "Sam stares at a freshly decorated cake Grandma is holding. His eyes become huge and he smiles mischievously. Grandma places the cake on the table and turns slightly away. Sam slowly moves one finger toward the frosting while Jasmine gives him a strong suspicious side-eye."),
            (12, "Sam tries to take a tiny bit of frosting. His finger slips and a small piece of frosting flicks upward. Sam and Jasmine watch it with wide eyes. It lands gently on Sam's cheek and nose. Sam freezes in shock while Jasmine covers her mouth and giggles."),
            (11, "Grandma turns and sees Sam. She raises her eyebrows with a playful serious look. Sam gives his biggest innocent smile. Grandma smiles, wipes his face, then places a tiny dot of frosting on Sam's nose. Jasmine bursts into laughter and Sam and Grandma laugh too."),
        ],
    },
}


def api_key() -> str:
    key = os.getenv("OFOX_API_KEY", "").strip()
    if not key:
        raise SystemExit("Missing OFOX_API_KEY environment variable")
    return key


def reference_urls():
    raw = os.getenv("JASMINE_SAM_REFERENCE_URLS", "")
    return [x.strip() for x in raw.split(",") if x.strip()]


def submit_clip(prompt: str, duration: int) -> str:
    headers = {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL,
        "prompt": f"{STYLE} {prompt}",
        "duration": duration,
        "resolution": RESOLUTION,
        "aspect_ratio": "9:16",
        "generate_audio": False,
    }
    refs = reference_urls()
    if refs:
        payload["input_references"] = [
            {"type": "image_url", "image_url": {"url": url}} for url in refs[:9]
        ]
    if PROVIDER:
        payload["provider"] = {"type": PROVIDER}

    r = requests.post(f"{BASE_URL}/videos", headers=headers, json=payload, timeout=90)
    if not r.ok:
        raise RuntimeError(f"OFox submit failed {r.status_code}: {r.text[:800]}")
    body = r.json()
    task_id = body.get("id")
    if not task_id:
        raise RuntimeError(f"OFox returned no task id: {body}")
    return task_id


def wait_for_clip(task_id: str) -> str:
    headers = {"Authorization": f"Bearer {api_key()}"}
    deadline = time.time() + 1800
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/videos/{task_id}", headers=headers, timeout=60)
        if not r.ok:
            raise RuntimeError(f"OFox status failed {r.status_code}: {r.text[:800]}")
        body = r.json()
        status = str(body.get("status", "")).lower()
        if status in {"completed", "succeeded"}:
            for field in ("mirror_urls", "unsigned_urls"):
                urls = body.get(field) or []
                if urls:
                    return urls[0]
            raise RuntimeError(f"Task {task_id} completed but returned no video URL")
        if status in {"failed", "error", "cancelled", "canceled", "expired"}:
            raise RuntimeError(f"Task {task_id} failed: {json.dumps(body, ensure_ascii=False)[:1200]}")
        time.sleep(POLL_SECONDS)
    raise TimeoutError(f"Timed out waiting for OFox task {task_id}")


def download(url: str, path: Path):
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        with path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)


def concat(clips, output: Path):
    list_file = output.parent / "concat.txt"
    list_file.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in clips), encoding="utf-8")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-an", "-movflags", "+faststart", str(output)
    ]
    subprocess.run(cmd, check=True)


def generate_episode(number: str, out_dir: Path):
    episode = SCENARIOS[number]
    episode_dir = out_dir / f"episode_{number}"
    episode_dir.mkdir(parents=True, exist_ok=True)
    clips = []
    print(f"Generating Episode {number}: {episode['title']}")
    for idx, (duration, action) in enumerate(episode["clips"], 1):
        print(f"  submitting clip {idx}/3 ({duration}s)...")
        task_id = submit_clip(action, duration)
        print(f"  task {task_id}; waiting...")
        url = wait_for_clip(task_id)
        clip_path = episode_dir / f"clip_{idx:02d}.mp4"
        download(url, clip_path)
        clips.append(clip_path)
        print(f"  saved {clip_path}")
    final_path = episode_dir / f"Jasmine_Sam_Episode_{number}.mp4"
    concat(clips, final_path)
    print(f"DONE: {final_path}")
    return final_path


def main():
    parser = argparse.ArgumentParser(description="Generate Jasmine & Sam episodes with OFox Seedance Mini")
    parser.add_argument("episodes", nargs="*", default=["4", "5", "6", "7"], choices=SCENARIOS.keys())
    parser.add_argument("--out", default="storage/jasmine_sam")
    args = parser.parse_args()

    if not reference_urls():
        print("WARNING: JASMINE_SAM_REFERENCE_URLS is empty. Character consistency will be weaker.", file=sys.stderr)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for ep in args.episodes:
        generate_episode(ep, out_dir)


if __name__ == "__main__":
    main()
