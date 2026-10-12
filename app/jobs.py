"""Background job manager: long syntheses run in worker threads with progress."""
import os
import shutil
import threading
import time
import uuid

from . import engine
from . import db

OUTPUT_DIR = os.environ.get("TTS_OUTPUT_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

_jobs = {}
_lock = threading.Lock()


def _run(job_id: str, text: str, voice_key: str, speed: float, output_format: str, title: str):
    job = _jobs[job_id]
    try:
        job["status"] = "downloading_voice"
        ext = "mp3" if output_format == "mp3" else "wav"
        tmp_out = os.path.join(OUTPUT_DIR, f".tmp_{job_id}.{ext}")

        def progress(done, total):
            job["status"] = "synthesizing"
            job["done"] = done
            job["total"] = total

        job["status"] = "synthesizing"
        result = engine.synthesize(
            text, voice_key, speed=speed, output_format=output_format,
            out_path=tmp_out, progress_cb=progress,
        )
        final_name = f"{job_id}.{ext}"
        final_path = os.path.join(OUTPUT_DIR, final_name)
        if os.path.exists(final_path):
            os.unlink(final_path)
        shutil.move(tmp_out, final_path)

        rec_id = db.add_record(
            title=title or text[:60],
            text_preview=text[:300],
            voice=voice_key,
            speed=speed,
            duration=result["duration"],
            chars=result["chars"],
            format=output_format,
            filename=final_name,
        )
        job["status"] = "done"
        job["record_id"] = rec_id
        job["filename"] = final_name
        job["duration"] = result["duration"]
    except Exception as e:  # noqa: BLE001
        job["status"] = "failed"
        job["error"] = str(e)
    finally:
        job["finished_at"] = time.time()


def create_job(text: str, voice_key: str, speed: float, output_format: str, title: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "done": 0,
            "total": 0,
            "created_at": time.time(),
        }
    t = threading.Thread(
        target=_run,
        args=(job_id, text, voice_key, speed, output_format, title),
        daemon=True,
    )
    t.start()
    return job_id


def get_job(job_id: str):
    with _lock:
        return dict(_jobs.get(job_id, {}))


def cleanup_old_jobs(max_age_hours: int = 72):
    cutoff = time.time() - max_age_hours * 3600
    with _lock:
        for jid in [j for j, v in _jobs.items()
                    if v.get("finished_at", 0) < cutoff and v.get("status") in ("done", "failed")]:
            del _jobs[jid]
