"""Fahad's Self-Hosted TTS Platform — FastAPI app."""
import os
import shutil

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db, engine, jobs, songs
from . import voices as voice_catalog

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title="Fahad TTS Studio", version="1.0.0")
db.init()


class SynthRequest(BaseModel):
    text: str = Field(min_length=1, max_length=engine.MAX_CHARS)
    voice: str = Field(default=voice_catalog.DEFAULT_VOICE)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    format: str = Field(default="mp3", pattern="^(mp3|wav)$")
    title: str = Field(default="", max_length=120)


class PreviewRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    voice: str = Field(default=voice_catalog.DEFAULT_VOICE)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


@app.get("/api/voices")
def api_voices():
    return {"voices": voice_catalog.voice_list(), "languages": voice_catalog.languages()}


@app.get("/api/limits")
def api_limits():
    return {"max_chars": engine.MAX_CHARS}


@app.post("/api/preview")
def api_preview(req: PreviewRequest):
    if req.voice not in voice_catalog.voice_ids():
        raise HTTPException(400, "Unknown voice")
    try:
        result = engine.preview(req.text, req.voice, req.speed)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, str(e))
    return FileResponse(result["path"], media_type="audio/mpeg",
                        filename="preview.mp3")


@app.post("/api/jobs")
def api_create_job(req: SynthRequest):
    if req.voice not in voice_catalog.voice_ids():
        raise HTTPException(400, "Unknown voice")
    job_id = jobs.create_job(req.text, req.voice, req.speed, req.format, req.title)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def api_job_status(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@app.get("/api/jobs/{job_id}/download")
def api_job_download(job_id: str):
    job = jobs.get_job(job_id)
    if not job or job.get("status") != "done":
        raise HTTPException(404, "Audio not ready")
    path = os.path.join(jobs.OUTPUT_DIR, job["filename"])
    if not os.path.exists(path):
        raise HTTPException(404, "File missing")
    media = "audio/mpeg" if path.endswith(".mp3") else "audio/wav"
    return FileResponse(path, media_type=media, filename=f"fahad-tts-{job_id}.{path.rsplit('.', 1)[-1]}")


@app.get("/api/history")
def api_history():
    return {"items": db.list_records()}


@app.get("/api/history/{rec_id}/download")
def api_history_download(rec_id: int):
    rec = db.get_record(rec_id)
    if not rec:
        raise HTTPException(404, "Not found")
    path = os.path.join(jobs.OUTPUT_DIR, rec["filename"])
    if not os.path.exists(path):
        raise HTTPException(404, "File missing")
    media = "audio/mpeg" if path.endswith(".mp3") else "audio/wav"
    return FileResponse(path, media_type=media, filename=f"fahad-tts-{rec_id}.{rec['format']}")


@app.delete("/api/history/{rec_id}")
def api_history_delete(rec_id: int):
    rec = db.get_record(rec_id)
    if not rec:
        raise HTTPException(404, "Not found")
    path = os.path.join(jobs.OUTPUT_DIR, rec["filename"])
    if os.path.exists(path):
        os.unlink(path)
    db.delete_record(rec_id)
    return {"ok": True}


@app.get("/api/health")
def api_health():
    return {"ok": True, "engine": "piper"}


# --- Song Studio (ACE-Step, requires GPU) ---
class SongRequest(BaseModel):
    lyrics: str = Field(min_length=1, max_length=5000)
    genre: str = Field(default="pop, happy, upbeat", max_length=200)
    voice: str = Field(default="male vocal", max_length=50)
    duration: int = Field(default=60, ge=15, le=300)


@app.get("/api/song/status")
def api_song_gpu_status():
    return {"gpu_available": songs.gpu_available()}


@app.post("/api/song/generate")
def api_song_generate(req: SongRequest):
    try:
        job_id = songs.create_song_job(req.lyrics, req.genre, req.voice, req.duration)
        return {"job_id": job_id}
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/song/status/{job_id}")
def api_song_job_status(job_id: str):
    job = songs.SONG_JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "done": job["done"], "progress": job["progress"],
        "status_text": job["status_text"], "error": job["error"],
    }


@app.get("/api/song/download/{job_id}")
def api_song_download(job_id: str):
    job = songs.SONG_JOBS.get(job_id)
    if not job or not job.get("file"):
        raise HTTPException(status_code=404, detail="Song not ready")
    return FileResponse(job["file"], media_type="audio/mpeg", filename=f"song-{job_id}.mp3")


# --- frontend ---
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
