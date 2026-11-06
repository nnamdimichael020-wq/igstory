// IGStory Bot V2 — control panel
const $ = (id) => document.getElementById(id);
let mode = "view_stories";
let pollTimer = null;

function apiBase() {
  const v = $("api-url").value.trim().replace(/\/$/, "");
  return v || "";
}

async function api(path, opts = {}) {
  const res = await fetch(apiBase() + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  return res.json();
}

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    mode = btn.dataset.mode;
  });
});

$("run").addEventListener("click", async () => {
  $("run").disabled = true;
  try {
    const res = await api("/api/run", {
      method: "POST",
      body: JSON.stringify({ mode, link: $("link").value }),
    });
    if (res.error) {
      $("logs").textContent = "Error: " + res.error;
    }
    startPolling();
  } catch (e) {
    $("logs").textContent = "Cannot reach API: " + e.message + "\nSet the API URL field to where webapp.py is running.";
  } finally {
    $("run").disabled = false;
  }
});

$("stop").addEventListener("click", () => api("/api/stop", { method: "POST" }).then(startPolling));

function startPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(refresh, 1500);
  refresh();
}

async function refresh() {
  try {
    const s = await api("/api/status");
    $("status").textContent = s.status + (s.result != null ? ` (${s.result} actions)` : "");
    $("status").className = s.status;
    $("logs").textContent = (s.logs || []).join("\n") || "No runs yet.";
    $("logs").scrollTop = $("logs").scrollHeight;
    if (s.status !== "running") {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  } catch (e) {
    $("status").textContent = "api unreachable";
  }
}

refresh();
