/** Settings: only the service address, stored in the browser's own sync storage. */

const DEFAULT_API = "http://127.0.0.1:8000";

const field = document.getElementById("api");
const saved = document.getElementById("saved");

chrome.storage.sync.get({ apiUrl: DEFAULT_API }).then(({ apiUrl }) => {
  field.value = apiUrl;
});

document.getElementById("save").addEventListener("click", async () => {
  const apiUrl = field.value.trim() || DEFAULT_API;
  await chrome.storage.sync.set({ apiUrl });
  saved.textContent = "yadda saxlanıldı";
  setTimeout(() => (saved.textContent = ""), 1500);
});
