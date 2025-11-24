const BRIDGE_URL = "http://127.0.0.1:5001/notify";
const MAYRA_TOKEN = "replace_with_your_token_123";

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === "mayra_payload") {
    fetch(BRIDGE_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-MAYRA-TOKEN": MAYRA_TOKEN
      },
      body: JSON.stringify(msg.data)
    })
    .then(r => r.text())
    .then(t => console.log("Bridge response:", t))
    .catch(err => console.error("Bridge fetch error:", err));
  }
});
