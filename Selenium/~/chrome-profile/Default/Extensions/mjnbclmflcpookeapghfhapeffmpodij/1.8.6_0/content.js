//const readyPromise = new Promise((resolve) => {
//  window.addEventListener("message", (e) => {
//    if (e?.data?.type === "ready") {
//      resolve();
//    }
//  });
//});
//
//const script = document.createElement("script");
//script.src = chrome.runtime.getURL("injected_content.js");
//document.documentElement.appendChild(script);
//
//chrome.runtime.sendMessage({ type: "getTrackingCode" }, (code) => {
//  if (!code) {
//    return;
//  }
//
//  readyPromise.then(() => postMessage({ type: "track", code }, "*"));
//});
