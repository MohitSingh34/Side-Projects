console.log("Mayra content script active");

function extractJSON(text) {
  const s = text.indexOf("{");
  const e = text.lastIndexOf("}");
  if (s === -1 || e === -1 || e <= s) return null;
  try { return JSON.parse(text.slice(s, e + 1)); }
  catch { return null; }
}

const observer = new MutationObserver(muts => {
  for (const m of muts) {
    for (const n of m.addedNodes) {
      if (!(n instanceof HTMLElement)) continue;
      const t = n.innerText || "";
      const j = extractJSON(t);
      if (j && (j.notify || j.cmd)) {
        console.log("Sending JSON to background:", j);
        chrome.runtime.sendMessage({ type: "mayra_payload", data: j });
      }
    }
  }
});

observer.observe(document.body, { childList: true, subtree: true });
