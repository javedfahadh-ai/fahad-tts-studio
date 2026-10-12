"""Pre-download voice models so first generation is instant.

Usage:
    python scripts/download_voices.py              # starred voices only
    python scripts/download_voices.py --all        # every curated voice
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.voices import VOICES  # noqa: E402

VOICES_DIR = os.environ.get("TTS_VOICES_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "voices"))


def main():
    only_starred = "--all" not in sys.argv
    todo = [(k, n) for (k, n, _, _, _, s) in VOICES if (s or not only_starred)]
    os.makedirs(VOICES_DIR, exist_ok=True)
    print(f"Downloading {len(todo)} voices to {VOICES_DIR} ...")
    for key, name in todo:
        target = os.path.join(VOICES_DIR, f"{key}.onnx")
        if os.path.exists(target):
            print(f"  ✓ {name} (cached)")
            continue
        print(f"  ↓ {name} ...", flush=True)
        try:
            subprocess.run(
                [sys.executable, "-m", "piper.download_voices",
                 "--download-dir", VOICES_DIR, key],
                check=True, capture_output=True, timeout=900,
            )
            print(f"  ✓ {name}")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ {name}: {e.stderr.decode()[-200:] if e.stderr else e}")


if __name__ == "__main__":
    main()
