/** The popup: a scratch pad for text that is not in a field on the page. */

const text = document.getElementById("text");
const fix = document.getElementById("fix");
const copy = document.getElementById("copy");
const status = document.getElementById("status");

fix.addEventListener("click", async () => {
  const value = text.value.trim();
  if (!value) return;

  fix.disabled = true;
  status.textContent = "…";

  const reply = await chrome.runtime.sendMessage({ type: "restore", text: value });

  if (reply?.ok) {
    text.value = reply.text;
    const count = reply.changes.length;
    status.textContent = count ? `${count} söz dəyişdi` : "dəyişiklik yoxdur";
  } else {
    status.textContent = reply?.error ?? "xəta";
  }

  fix.disabled = false;
});

copy.addEventListener("click", async () => {
  await navigator.clipboard.writeText(text.value);
  status.textContent = "kopyalandı";
});
