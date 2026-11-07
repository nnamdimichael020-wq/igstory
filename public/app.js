// IGStory Bot V2 — control panel
const $ = (id) => document.getElementById(id);
let modes = new Set(["view_stories"]);
let pollTimer = null;

function apiBase() {
  const v = $("api-url").value.trim().replace(/\/$/, "");
  return v || "";
}

async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
  const key = $("api-key").value.trim();
  if (key) headers["Authorization"] = "Bearer " + key;
  const res = await fetch(apiBase() + path, { ...opts, headers });
  return res.json();
}

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const m = btn.dataset.mode;
    if (modes.has(m)) { modes.delete(m); btn.classList.remove("active"); }
    else { modes.add(m); btn.classList.add("active"); }
    if (modes.size === 0) { modes.add(m); btn.classList.add("active"); } // keep at least one
  });
});

$("run").addEventListener("click", async () => {
  $("run").disabled = true;
  try {
    const res = await api("/api/run", {
      method: "POST",
      body: JSON.stringify({
        modes: [...modes],
        link: $("link").value,
        views: $("views").value,
        interval: $("interval").value,
        like_ratio: parseFloat($("like-ratio").value) || 0,
        comment_ratio: parseFloat($("comment-ratio").value) || 0,
      }),
    });
    if (res.error) $("logs").textContent = "Error: " + res.error;
    startPolling();
  } catch (e) {
    $("logs").textContent = "Cannot reach API: " + e.message + "\nSet the API URL field to where webapp.py is running.";
  } finally {
    $("run").disabled = false;
  }
});

function currentJob(s) {
  const jobs = s.jobs || [];
  return jobs[jobs.length - 1] || null;
}
function jobId() {
  return null; // operate on latest job
}

$("stop").addEventListener("click", () => api("/api/stop", { method: "POST", body: "{}" }).then(startPolling));
$("clear").addEventListener("click", () => api("/api/clear", { method: "POST" }).then(refresh));
$("pause").addEventListener("click", () => api("/api/pause", { method: "POST", body: "{}" }).then(refresh));
$("resume").addEventListener("click", () => api("/api/resume", { method: "POST", body: "{}" }).then(refresh));
$("mute").addEventListener("click", async () => {
  const s = await api("/api/status");
  const j = currentJob(s);
  const muted = j ? !j.muted : true;
  $("mute").textContent = muted ? "🔔 Unmute" : "🔕 Mute";
  await api("/api/mute", { method: "POST", body: JSON.stringify({ muted }) });
  refresh();
});

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(refresh, 1500);
  refresh();
}

async function refresh() {
  try {
    const s = await api("/api/status");
    const jobs = s.jobs || [];
    const cur = jobs[jobs.length - 1] || { status: "idle", logs: [], progress: { cycle: 0, actions: 0 } };
    const anyActive = jobs.some((j) => ["running", "queued", "paused"].includes(j.status));
    $("status").textContent = `${cur.status} · queue ${s.queue} · workers ${s.workers} · total ${s.stats.total_actions} actions`;
    $("status").className = cur.status;
    const hb = s.heartbeat || {};
    const hbEl = $("heartbeat");
    hbEl.textContent = hb.last ? `♥ synced ${hb.last} (#${hb.count})` : "♥ syncing…";
    hbEl.classList.toggle("alive", !!hb.last);
    const p = cur.progress || { cycle: 0, actions: 0 };
    $("progress").textContent = cur.status === "idle" ? "" :
      `progress: cycle ${p.cycle} · ${p.actions} actions this job${cur.paused ? " · ⏸ paused" : ""}${cur.muted ? " · 🔕 muted" : ""}`;
    $("logs").textContent = (cur.logs || []).join("\n") || "No runs yet.";
    $("logs").scrollTop = $("logs").scrollHeight;
    const h = (s.history || []).slice(-10).reverse()
      .map((j) => `[${j.time}] #${j.id} c${j.cycle} ${j.modes.join("+")} -> ${j.status}${j.result != null ? ` (${j.result})` : ""}${j.error ? " ERR: " + j.error : ""}`)
      .join("\n");
    $("history").textContent = h || "No history yet.";
    if (!anyActive) { clearInterval(pollTimer); pollTimer = null; }
  } catch (e) {
    $("status").textContent = "api unreachable";
    $("heartbeat").textContent = "♥ offline";
  }
}

refresh();
