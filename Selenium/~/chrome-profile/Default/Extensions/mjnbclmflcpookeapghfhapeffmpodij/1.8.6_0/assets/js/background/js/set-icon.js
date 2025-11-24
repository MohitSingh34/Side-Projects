var intervalID = !1, iconState = 0;
export default function setIcon(b) {
    "connecting" === b && !1 === intervalID ? (iconState = 1, chrome.action.setIcon({ path: "assets/img/icon/signal/0.png" }), intervalID = setInterval(function () { 0 == iconState ? (chrome.action.setIcon({ path: "assets/img/icon/signal/0.png" }), iconState = 1) : 1 == iconState ? (chrome.action.setIcon({ path: "assets/img/icon/signal/1.png" }), iconState = 2) : 2 == iconState ? (chrome.action.setIcon({ path: "assets/img/icon/signal/2.png" }), iconState = 3) : 3 == iconState && (chrome.action.setIcon({ path: "assets/img/icon/signal/3.png" }), iconState = 0) }, 400)) : intervalID && (clearInterval(intervalID), intervalID = !1); "connected" === b && chrome.action.setIcon({ path: "assets/img/icon/icon_48.png" }); "ready" === b && chrome.action.setIcon({ path: "assets/img/icon/icon_BW_48.png" }); "noConnection" === b && chrome.action.setIcon({ path: "assets/img/icon/icon_error_48.png" })
}

