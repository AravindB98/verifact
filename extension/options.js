const api = document.getElementById("api");
chrome.storage.sync.get({ apiBase: "http://127.0.0.1:8000" }, ({ apiBase }) => {
  api.value = apiBase;
});
document.getElementById("save").addEventListener("click", () => {
  chrome.storage.sync.set({ apiBase: api.value.trim() || "http://127.0.0.1:8000" }, () => {
    const s = document.getElementById("saved");
    s.style.opacity = 1;
    setTimeout(() => (s.style.opacity = 0), 1500);
  });
});
