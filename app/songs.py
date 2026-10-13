"""Song generation via ACE-Step (requires GPU). Gracefully disabled without GPU."""
import os
import shutil
import subprocess
import threading
import time
import uuid

SONG_JOBS = {}
SONG_DIR = os.environ.get("SONG_DIR", "/data/songs")


def gpu_available() -> bool:
    """Check if CUDA GPU is available."""
    # Check nvidia-smi
    if shutil.which("nvidia-smi"):
        try:
            r = subprocess.run(["nvidia-smi", "-L"], capture_output=True, timeout=5)
            if r.returncode == 0 and b"GPU" in r.stdout:
                return True
        except Exception:
            pass
    # Check torch cuda
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False


def _run_song_job(job_id: str, lyrics: str, genre: str, voice: str, duration: int):
    """Background worker: generate song via ACE-Step."""
    job = SONG_JOBS[job_id]
    try:
        job["status_text"] = "Loading ACE-Step model…"
        job["progress"] = 20

        # Import here (only when GPU available)
        from acestep import ACESTEP
        model = ACESTEP()

        job["status_text"] = "Composing your song…"
        job["progress"] = 40

        result = model.generate(
            lyrics=lyrics,
            tags=f"{genre}, {voice}",
            duration=duration,
        )

        job["status_text"] = "Saving…"
        job["progress"] = 90

        os.makedirs(SONG_DIR, exist_ok=True)
        out_path = os.path.join(SONG_DIR, f"{job_id}.mp3")
        result.save(out_path)

        job["done"] = True
        job["progress"] = 100
        job["status_text"] = "Done!"
        job["file"] = out_path
    except Exception as e:
        job["done"] = True
        job["error"] = str(e)
        job["status_text"] = f"Error: {e}"


def create_song_job(lyrics: str, genre: str, voice: str, duration: int) -> str:
    if not gpu_available():
        raise RuntimeError("Song generation requires a GPU server. Connect your GPU to activate.")
    job_id = uuid.uuid4().hex[:12]
    SONG_JOBS[job_id] = {
        "done": False, "progress": 5,
        "status_text": "Queued…", "error": None, "file": None,
    }
    t = threading.Thread(target=_run_song_job, args=(job_id, lyrics, genre, voice, duration), daemon=True)
    t.start()
    return job_id
