const COLORS = {
  high_credibility: "#2fbf71",
  moderate_credibility: "#e8b931",
  low_credibility: "#e0533d",
  very_low_credibility: "#e0533d",
  insufficient_evidence: "#93a0be",
};

async function apiBase() {
  const { apiBase } = await chrome.storage.sync.get({ apiBase: "http://127.0.0.1:8000" });
  return apiBase.replace(/\/$/, "");
}

async function currentTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function el(id) { return document.getElementById(id); }

(async () => {
  const tab = await currentTab();
  el("url").textContent = tab?.url || "no tab";

  el("check").addEventListener("click", async () => {
    const btn = el("check");
    const err = el("err");
    err.style.display = "none";
    btn.disabled = true;
    btn.textContent = "Verifying…";
    try {
      const base = await apiBase();
      const resp = await fetch(`${base}/api/v1/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: tab.url }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "Analysis failed");
      render(data);
    } catch (e) {
      err.textContent =
        e.message.includes("Failed to fetch")
          ? "Could not reach the VeriFact engine. Start it with `verifact serve` (see Settings for the API address)."
          : e.message;
      err.style.display = "block";
    } finally {
      btn.disabled = false;
      btn.textContent = "Verify this page";
    }
  });
})();

function render(r) {
  const box = el("verdict");
  box.style.display = "block";
  const color = COLORS[r.verdict] || "#93a0be";
  el("v-title").textContent = r.verdict_label;
  el("v-title").style.color = color;
  el("v-score").textContent = r.score == null ? "—" : `${r.score} / 100`;
  el("v-score").style.color = color;
  el("v-sum").textContent = r.summary;
  el("v-signals").innerHTML = (r.signals || [])
    .filter((s) => s.status === "ok" && s.score != null)
    .map((s) => {
      const b = document.createElement("b");
      b.textContent = Math.round(s.score);
      const div = document.createElement("div");
      div.className = "sig";
      div.appendChild(b);
      div.appendChild(document.createTextNode(" " + s.title + " — " + s.summary));
      return div.outerHTML;
    })
    .join("");
}
