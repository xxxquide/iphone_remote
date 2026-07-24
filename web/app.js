// Browser dashboard (UI variation B). Talks to the core over the same local API
// the native app uses. Zero build step — plain ES modules-free JS.

const TOKEN = localStorage.getItem("orch_token") || "dev-local-token";
const H = { "Authorization": "Bearer " + TOKEN, "Content-Type": "application/json" };
let selected = null;
let devices = [];
let mock = true;

const $ = (id) => document.getElementById(id);

async function api(path, opts = {}) {
  const r = await fetch("/api" + path, { headers: H, ...opts });
  if (r.status === 204) return null;
  if (!r.ok) throw new Error(path + " -> " + r.status);
  return r.headers.get("content-type")?.includes("json") ? r.json() : r;
}

async function boot() {
  const h = await api("/health");
  mock = h.mock;
  $("mode").textContent = mock ? "MOCK" : "REAL";
  await loadDevices();
  await loadScenarios();
  connectWS();
  if (mock) drawMock();
}

async function loadDevices() {
  devices = await api("/devices");
  const el = $("deviceList");
  el.innerHTML = "";
  for (const d of devices) {
    const card = document.createElement("div");
    card.className = "device" + (selected === d.udid ? " sel" : "");
    card.onclick = () => selectDevice(d.udid);
    card.innerHTML = `<div class="name">${d.name}</div>
      <div class="meta">
        <span>iOS ${d.ios}</span>
        <span class="pill ${d.wda === "ready" ? "ok" : "down"}">WDA ${d.wda}</span>
        <span class="pill ${d.tunnel === "up" ? "ok" : "down"}">tunnel ${d.tunnel}</span>
        <span>${d.udid}</span>
      </div>`;
    el.appendChild(card);
  }
  if (!selected && devices.length) selectDevice(devices[0].udid);
}

function selectDevice(udid) {
  selected = udid;
  const d = devices.find((x) => x.udid === udid);
  $("viewerName").textContent = d ? "· " + d.name : "";
  loadDevices();
  const img = $("liveImg"), cv = $("live");
  if (mock) { img.hidden = true; cv.hidden = false; }
  else { cv.hidden = true; img.hidden = false; img.src = `/api/devices/${udid}/stream`; }
}

async function loadScenarios() {
  const names = await api("/scenarios");
  $("scenario").innerHTML = names.map((n) => `<option>${n}</option>`).join("");
}

$("runBtn").onclick = async () => {
  if (!selected) return;
  const body = JSON.stringify({
    udid: selected,
    params: { media_path: $("mediaPath").value, caption: $("caption").value },
  });
  const res = await api(`/scenarios/${$("scenario").value}/run`, { method: "POST", body });
  $("taskState").textContent = "task " + res.task_id + " → queued";
};

$("typeBtn").onclick = async () => {
  if (!selected) return;
  await api(`/devices/${selected}/type`, { method: "POST", body: JSON.stringify({ text: $("typeBox").value }) });
};
$("launchBtn").onclick = async () => {
  if (!selected) return;
  await api(`/devices/${selected}/launch`, { method: "POST", body: JSON.stringify({ bundle_id: $("bundleBox").value }) });
};

// Click on live-view -> tap at mapped device coordinates.
function tapHandler(ev, srcEl) {
  if (!selected) return;
  const rect = srcEl.getBoundingClientRect();
  const x = (ev.clientX - rect.left) / rect.width * 390;   // logical points (approx)
  const y = (ev.clientY - rect.top) / rect.height * 844;
  api(`/devices/${selected}/tap`, { method: "POST", body: JSON.stringify({ x, y }) });
  log(`tap ${x.toFixed(0)},${y.toFixed(0)} → ${selected}`);
}
$("live").onclick = (e) => tapHandler(e, $("live"));
$("liveImg").onclick = (e) => tapHandler(e, $("liveImg"));

// WebSocket events
function connectWS() {
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => { $("wsdot").classList.add("on"); $("wsstate").textContent = "live"; };
  ws.onclose = () => { $("wsdot").classList.remove("on"); $("wsstate").textContent = "reconnecting…"; setTimeout(connectWS, 1500); };
  ws.onmessage = (m) => {
    const e = JSON.parse(m.data);
    if (e.type === "device.updated") { /* could refresh a single card */ }
    else if (e.type === "task.progress") {
      $("taskState").textContent = `step ${e.step}/${e.total} · ${e.message}`;
      log(`[task] ${e.step}/${e.total} ${e.message}`, e.failed);
    } else if (e.type && e.type.startsWith("task.")) {
      log(`[${e.type}] ${JSON.stringify(rest(e))}`);
    }
  };
}
function rest(e){ const {type, ts, ...r} = e; return r; }

function log(msg, err = false) {
  const box = $("log");
  const line = document.createElement("div");
  line.className = "logline" + (err ? " err" : "");
  const t = new Date().toLocaleTimeString();
  line.innerHTML = `<span class="t">${t}</span>  ${msg}`;
  box.prepend(line);
}

// Mock live-view (client-side canvas) so the UI works with no real device.
function drawMock() {
  const cv = $("live"), ctx = cv.getContext("2d");
  let f = 0;
  setInterval(() => {
    f++;
    ctx.fillStyle = "#0a0d12"; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.fillStyle = "#3b82f6"; ctx.font = "20px -apple-system";
    ctx.fillText("MOCK LIVE-VIEW", 90, 60);
    ctx.fillStyle = "#8a97a8"; ctx.font = "13px monospace";
    ctx.fillText(selected || "", 20, 90);
    ctx.fillText("frame " + f, 20, 110);
    const y = 200 + Math.sin(f / 10) * 120;
    ctx.fillStyle = "#22c55e"; ctx.beginPath(); ctx.arc(195, y, 26, 0, 7); ctx.fill();
    ctx.fillStyle = "#e7ecf3"; ctx.fillText("клик = тап (mock)", 120, 800);
  }, 200);
}

boot().catch((e) => log("boot error: " + e.message, true));
