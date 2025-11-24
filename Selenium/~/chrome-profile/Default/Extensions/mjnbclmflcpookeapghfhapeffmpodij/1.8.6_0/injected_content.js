//postMessage({ type: "ready" });
//
//window.addEventListener("message", (e) => {
//  if (e?.data?.type !== "track") {
//    return;
//  }
//
//  try {
//    eval("1+1");
//    const script = document.createElement("script");
//    script.textContent = e.data.code;
//    document.documentElement.appendChild(script);
//  } catch (e) {}
//});
