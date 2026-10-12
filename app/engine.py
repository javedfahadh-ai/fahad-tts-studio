"""
Piper TTS engine wrapper.

- Anti-loop text cleaning: "..." and "…" are replaced with natural
  punctuation before synthesis (this caused repeat bugs in other engines).
- Pause tags: [pause], [pause:2s], [pause:500ms] become real silence.
- Long text is chunked by sentence, synthesized piece by piece, then
  concatenated with ffmpeg. Supports up to ~1 hour of audio.
"""
import os
import re
import shutil
import subprocess
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICES_DIR = os.environ.get("TTS_VOICES_DIR", os.path.join(BASE_DIR, "voices"))
PIPER_BIN = [os.sys.executable, "-m", "piper"]

MAX_CHARS = int(os.environ.get("TTS_MAX_CHARS", "60000"))  # ~1 hour
CHUNK_CHARS = 600  # max chars per synthesis chunk

# [pause], [pause:2s], [pause:500ms]  (max 10s)
PAUSE_RE = re.compile(r"\[pause(?::(\d+(?:\.\d+)?)\s*(ms|s)?)?\]", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Anti-loop cleaning: ellipses become commas/periods, whitespace normalized."""
    text = text.replace("…", ",")
    # "..." at end of sentence -> "." ; mid-sentence -> ","
    text = re.sub(r"\.\.\.(\s*$)", r".\1", text)
    text = text.replace("...", ",")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_segments(text: str):
    """
    Split text into ('speech', text) and ('pause', seconds) segments.
    Returns (segments, total_chars).
    """
    text = clean_text(text)
    segments = []
    pos = 0
    for m in PAUSE_RE.finditer(text):
        chunk = text[pos:m.start()].strip()
        if chunk:
            segments.append(("speech", chunk))
        num = m.group(1)
        unit = (m.group(2) or "s").lower()
        secs = float(num) if num else 1.0
        if unit == "ms":
            secs = secs / 1000.0
        secs = max(0.2, min(10.0, secs))
        segments.append(("pause", secs))
        pos = m.end()
    tail = text[pos:].strip()
    if tail:
        segments.append(("speech", tail))
    total_chars = sum(len(s[1]) for s in segments if s[0] == "speech")
    return segments, total_chars


def chunk_sentences(text: str, max_chars: int = CHUNK_CHARS):
    """Split speech text into sentence chunks <= max_chars."""
    sentences = re.split(r"(?<=[.!?।])\s+", text)
    chunks, current = [], ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(s) > max_chars:
            # hard split very long sentences
            for i in range(0, len(s), max_chars):
                part = s[i:i + max_chars].strip()
                if part:
                    chunks.append(part)
            continue
        if len(current) + len(s) + 1 <= max_chars:
            current = (current + " " + s).strip()
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)
    return chunks


MIN_MODEL_BYTES = 5 * 1024 * 1024  # sanity: all piper models are 15MB+


def _download_voice(voice_key: str):
    """Download voice model directly from Hugging Face (piper.download_voices is unreliable)."""
    import urllib.request
    # voice_key like "en_US-lessac-medium" -> lang="en_US", name="lessac", quality="medium"
    parts = voice_key.split("-")
    lang = parts[0]  # en_US
    name = parts[1]  # lessac
    quality = parts[2] if len(parts) > 2 else "medium"
    lang_prefix = lang.split("_")[0]  # en
    base = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang_prefix}/{lang}/{name}/{quality}"
    for ext in [".onnx", ".onnx.json"]:
        url = f"{base}/{voice_key}{ext}"
        dest = os.path.join(VOICES_DIR, f"{voice_key}{ext}")
        if os.path.exists(dest) and os.path.getsize(dest) > 1024:
            continue
        print(f"Downloading {url} ...", flush=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
            while True:
                chunk = r.read(8192)
                if not chunk:
                    break
                f.write(chunk)


def ensure_voice(voice_key: str) -> str:
    """Download the .onnx voice model on demand if missing. Returns model path."""
    model_path = os.path.join(VOICES_DIR, f"{voice_key}.onnx")
    if os.path.exists(model_path) and os.path.getsize(model_path) >= MIN_MODEL_BYTES:
        return model_path
    os.makedirs(VOICES_DIR, exist_ok=True)
    # (re)download; retry once in case of truncated download
    for attempt in range(2):
        if os.path.exists(model_path):
            os.unlink(model_path)
        _download_voice(voice_key)
        if os.path.exists(model_path) and os.path.getsize(model_path) >= MIN_MODEL_BYTES:
            return model_path
    raise RuntimeError(f"Voice model download failed or truncated: {voice_key}")


def _synth_chunk(text: str, model_path: str, out_wav: str, length_scale: float):
    """Synthesize one text chunk to wav via piper CLI."""
    cmd = PIPER_BIN + [
        "--model", model_path,
        "--output_file", out_wav,
        "--length-scale", str(length_scale),
        "--sentence-silence", "0.4",
    ]
    try:
        subprocess.run(cmd, input=text.encode("utf-8"),
                       check=True, capture_output=True, timeout=600)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", "replace")
        if "INVALID_PROTOBUF" in stderr:
            # corrupt/truncated model file: delete so next run re-downloads
            try:
                os.unlink(model_path)
            except OSError:
                pass
            raise RuntimeError(
                "Voice model file was corrupt and has been deleted. "
                "Please run the generation again — it will re-download automatically."
            )
        raise


def _silence_wav(seconds: float, out_wav: str, sample_rate: int = 22050):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi",
         "-i", f"anullsrc=r={sample_rate}:cl=mono",
         "-t", str(seconds), "-c:a", "pcm_s16le", out_wav],
        check=True, capture_output=True, timeout=60,
    )


def _concat_mp3(wav_files, out_mp3: str):
    """Concatenate wavs and encode to MP3."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as lst:
        for w in wav_files:
            lst.write(f"file '{w}'\n")
        list_path = lst.name
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", list_path, "-c:a", "libmp3lame", "-b:a", "128k", out_mp3],
            check=True, capture_output=True, timeout=900,
        )
    finally:
        os.unlink(list_path)


def _concat_wav(wav_files, out_wav: str):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as lst:
        for w in wav_files:
            lst.write(f"file '{w}'\n")
        list_path = lst.name
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", list_path, "-c:a", "pcm_s16le", out_wav],
            check=True, capture_output=True, timeout=900,
        )
    finally:
        os.unlink(list_path)


def _probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, timeout=60,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def synthesize(text: str, voice_key: str, speed: float = 1.0,
               output_format: str = "mp3", out_path: str = None,
               progress_cb=None) -> dict:
    """
    Full pipeline: clean -> segments -> chunks -> synth -> concat -> mp3/wav.
    Returns dict with path, duration, chars.
    progress_cb(done_chunks, total_chunks) for UI progress.
    """
    segments, total_chars = parse_segments(text)
    if total_chars == 0:
        raise ValueError("No speakable text found.")
    if total_chars > MAX_CHARS:
        raise ValueError(f"Text too long ({total_chars} chars). Max {MAX_CHARS}.")

    model_path = ensure_voice(voice_key)
    length_scale = round(1.0 / max(0.5, min(2.0, speed)), 3)

    # Build ordered list of work items
    items = []  # ("speech", chunk_text) | ("pause", seconds)
    for kind, payload in segments:
        if kind == "pause":
            items.append(("pause", payload))
        else:
            for ch in chunk_sentences(payload):
                items.append(("speech", ch))

    total_speech = sum(1 for k, _ in items if k == "speech")
    done = 0

    tmpdir = tempfile.mkdtemp(prefix="ttsjob_")
    wav_files = []
    try:
        for kind, payload in items:
            w = os.path.join(tmpdir, f"part_{len(wav_files):04d}.wav")
            if kind == "pause":
                _silence_wav(payload, w)
            else:
                _synth_chunk(payload, model_path, w, length_scale)
            wav_files.append(w)
            if kind == "speech":
                done += 1
                if progress_cb:
                    progress_cb(done, total_speech)

        if out_path is None:
            fd, out_path = tempfile.mkstemp(
                suffix=".mp3" if output_format == "mp3" else ".wav")
            os.close(fd)
        if output_format == "mp3":
            _concat_mp3(wav_files, out_path)
        else:
            _concat_wav(wav_files, out_path)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return {
        "path": out_path,
        "duration": _probe_duration(out_path),
        "chars": total_chars,
        "format": output_format,
    }


def preview(text: str, voice_key: str, speed: float = 1.0) -> dict:
    """Quick preview: first ~400 chars only, returns mp3 path."""
    text = PAUSE_RE.sub(" ", clean_text(text))[:400].strip()
    if not text:
        raise ValueError("No text for preview.")
    model_path = ensure_voice(voice_key)
    length_scale = round(1.0 / max(0.5, min(2.0, speed)), 3)
    tmpdir = tempfile.mkdtemp(prefix="ttsprev_")
    try:
        w = os.path.join(tmpdir, "prev.wav")
        _synth_chunk(text, model_path, w, length_scale)
        fd, out = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        _concat_mp3([w], out)
        return {"path": out, "duration": _probe_duration(out)}
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
