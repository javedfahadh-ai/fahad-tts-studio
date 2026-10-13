const $ = (id) => document.getElementById(id);

let ALL_VOICES = [];
let MAX_CHARS = 60000;
let pollTimer = null;

async function init() {
  const [vRes, lRes] = await Promise.all([
    fetch("/api/voices").then(r => r.json()),
    fetch("/api/limits").then(r => r.json()),
  ]);
  ALL_VOICES = vRes.voices;
  MAX_CHARS = lRes.max_chars;

  // language dropdown
  vRes.languages.forEach(l => {
    const o = document.createElement("option");
    o.value = l.code; o.textContent = l.name;
    $("langSelect").appendChild(o);
  });

  // default: English (US)
  $("langSelect").value = "en_US";
  renderVoices();

  $("langSelect").onchange = renderVoices;
  $("genderSelect").onchange = renderVoices;
  $("textInput").oninput = updateCount;
  $("speedRange").oninput = () =>
    ($("speedVal").textContent = parseFloat($("speedRange").value).toFixed(2) + "×");
  $("previewBtn").onclick = previewVoice;
  $("generateBtn").onclick = generate;
  updateCount();
  loadHistory();
}

function renderVoices() {
  const lang = $("langSelect").value;
  const gender = $("genderSelect").value;
  const list = ALL_VOICES.filter(v =>
    (!lang || v.lang === lang) && (!gender || v.gender === gender));
  const sel = $("voiceSelect");
  sel.innerHTML = "";
  // starred first
  list.sort((a, b) => (b.starred - a.starred) || a.name.localeCompare(b.name));
  list.forEach(v => {
    const o = document.createElement("option");
    o.value = v.id;
    o.textContent = (v.starred ? "★ " : "") + v.name + " · " + v.language;
    sel.appendChild(o);
  });
  $("voiceCount").textContent = `(${list.length})`;
  if (!list.length) {
    const o = document.createElement("option");
    o.textContent = "No voices match";
    sel.appendChild(o);
  }
}

function updateCount() {
  const n = $("textInput").value.length;
  $("charCount").textContent = `${n.toLocaleString()} / ${MAX_CHARS.toLocaleString()}`;
  $("charCount").style.color = n > MAX_CHARS ? "#ff6b6b" : "";
}

async function previewVoice() {
  const text = $("textInput").value.trim().slice(0, 400) || "Hello! This is a preview of my voice.";
  const btn = $("previewBtn");
  btn.disabled = true; btn.textContent = "Loading…";
  try {
    const res = await fetch("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        voice: $("voiceSelect").value,
        speed: parseFloat($("speedRange").value),
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const audio = $("previewAudio");
    audio.src = URL.createObjectURL(blob);
    audio.classList.remove("hidden");
    audio.play();
  } catch (e) {
    alert("Preview failed: " + e.message);
  } finally {
    btn.disabled = false; btn.textContent = "▶ Preview voice";
  }
}

async function generate() {
  const text = $("textInput").value.trim();
  if (!text) { alert("Please enter some text first."); return; }
  if (text.length > MAX_CHARS) { alert("Text is too long."); return; }
  const btn = $("generateBtn");
  btn.disabled = true; btn.textContent = "Starting…";
  try {
    const res = await fetch("/api/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        voice: $("voiceSelect").value,
        speed: parseFloat($("speedRange").value),
        format: $("formatSelect").value,
        title: $("titleInput").value.trim(),
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    const { job_id } = await res.json();
    $("jobCard").classList.remove("hidden");
    $("resultAudio").classList.add("hidden");
    $("downloadBtn").classList.add("hidden");
    pollJob(job_id);
  } catch (e) {
    alert("Failed to start: " + e.message);
    btn.disabled = false; btn.textContent = "⚡ Generate Audio";
  }
}

function pollJob(job_id) {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    const job = await fetch(`/api/jobs/${job_id}`).then(r => r.json());
    const bar = $("progressBar");
    const status = $("jobStatus");
    if (job.status === "done") {
      clearInterval(pollTimer);
      bar.style.width = "100%";
      status.textContent = `Done ✓ ${job.duration ? job.duration.toFixed(1) + "s audio" : ""}`;
      const audio = $("resultAudio");
      audio.src = `/api/jobs/${job_id}/download`;
      audio.classList.remove("hidden");
      const dl = $("downloadBtn");
      dl.href = `/api/jobs/${job_id}/download`;
      dl.classList.remove("hidden");
      const btn = $("generateBtn");
      btn.disabled = false; btn.textContent = "⚡ Generate Audio";
      loadHistory();
      $("jobCard").scrollIntoView({ behavior: "smooth" });
    } else if (job.status === "failed") {
      clearInterval(pollTimer);
      status.textContent = "Failed: " + (job.error || "unknown error");
      const btn = $("generateBtn");
      btn.disabled = false; btn.textContent = "⚡ Generate Audio";
    } else {
      const pct = job.total > 0 ? Math.round((job.done / job.total) * 100) : 5;
      bar.style.width = pct + "%";
      const label = {
        queued: "Queued…",
        downloading_voice: "Downloading voice model (first time only)…",
        synthesizing: `Synthesizing… ${job.done}/${job.total} parts`,
      }[job.status] || job.status;
      status.textContent = label;
    }
  }, 1500);
}

async function loadHistory() {
  const { items } = await fetch("/api/history").then(r => r.json());
  const box = $("historyList");
  box.innerHTML = items.length ? "" : '<div class="muted">No audios yet — your generations will appear here.</div>';
  items.forEach(it => {
    const div = document.createElement("div");
    div.className = "hist-item";
    const mins = Math.floor(it.duration / 60);
    const secs = Math.round(it.duration % 60);
    div.innerHTML = `
      <div class="info">
        <div class="title">${escapeHtml(it.title)}</div>
        <div class="meta">${escapeHtml(it.voice)} · ${mins}:${String(secs).padStart(2, "0")} ·
          ${(it.chars || 0).toLocaleString()} chars · ${new Date(it.created_at * 1000).toLocaleString()}</div>
      </div>
      <a class="btn primary" href="/api/history/${it.id}/download" download>⬇ ${it.format.toUpperCase()}</a>
      <button class="btn del" data-id="${it.id}">✕</button>`;
    box.appendChild(div);
  });
  box.querySelectorAll(".del").forEach(b => b.onclick = async () => {
    if (!confirm("Delete this audio?")) return;
    await fetch(`/api/history/${b.dataset.id}`, { method: "DELETE" });
    loadHistory();
  });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ---- Tab switching ----
document.querySelectorAll(".tab").forEach(t => t.onclick = () => {
  document.querySelectorAll(".tab").forEach(x => x.classList.remove("active"));
  t.classList.add("active");
  $("tab-tts").classList.toggle("hidden", t.dataset.tab !== "tts");
  $("tab-song").classList.toggle("hidden", t.dataset.tab !== "song");
  if (t.dataset.tab === "song") checkSongGPU();
});

// ---- Song Studio ----
async function checkSongGPU() {
  try {
    const r = await fetch("/api/song/status").then(r => r.json());
    $("gpuWarning").classList.toggle("hidden", r.gpu_available);
    $("songGenBtn").disabled = !r.gpu_available;
    if (!r.gpu_available) $("songGenBtn").textContent = "⏳ GPU Required";
  } catch (e) {
    $("gpuWarning").classList.remove("hidden");
  }
}

$("songGenBtn").onclick = async () => {
  const lyrics = $("songLyrics").value.trim();
  if (!lyrics) { alert("Please write some lyrics first!"); return; }
  $("songResultCard").classList.remove("hidden");
  $("songAudio").classList.add("hidden");
  $("songDownload").classList.add("hidden");
  $("songStatus").textContent = "Generating your song… (this takes 1-2 minutes)";
  $("songProgressBar").style.width = "10%";
  $("songGenBtn").disabled = true;
  try {
    const r = await fetch("/api/song/generate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        lyrics,
        genre: $("songGenre").value,
        voice: $("songVoice").value,
        duration: parseInt($("songDuration").value),
      }),
    }).then(r => r.json());
    if (r.error) throw new Error(r.error);
    pollSong(r.job_id);
  } catch (e) {
    $("songStatus").textContent = "Error: " + e.message;
    $("songGenBtn").disabled = false;
  }
};

async function pollSong(jobId) {
  const timer = setInterval(async () => {
    try {
      const s = await fetch(`/api/song/status/${jobId}`).then(r => r.json());
      $("songProgressBar").style.width = (s.progress || 10) + "%";
      $("songStatus").textContent = s.status_text || "Working…";
      if (s.done) {
        clearInterval(timer);
        $("songGenBtn").disabled = false;
        if (s.error) {
          $("songStatus").textContent = "Error: " + s.error;
        } else {
          $("songStatus").textContent = "Done! 🎵";
          $("songProgressBar").style.width = "100%";
          $("songAudio").src = `/api/song/download/${jobId}`;
          $("songAudio").classList.remove("hidden");
          $("songDownload").href = `/api/song/download/${jobId}`;
          $("songDownload").classList.remove("hidden");
        }
      }
    } catch (e) { /* keep polling */ }
  }, 3000);
}

init();
