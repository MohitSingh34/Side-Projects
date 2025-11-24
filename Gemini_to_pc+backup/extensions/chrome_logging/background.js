// background.js

let activeTabData = {}; // Current active tab ki info
const LOG_SAVE_INTERVAL = 30000; // Har 30 seconds mein save

function now() { return Date.now(); }

// 1. Session Shuru Karna
async function startSession(tabId) {
    if (activeTabData[tabId]) return; // Agar pehle se shuru hai toh kuch mat karo

    try {
        const tab = await chrome.tabs.get(tabId);
        // Only log http/https tabs
        if (!tab || !/^https?:\/\//.test(tab.url)) return; 

        activeTabData[tabId] = {
            url: tab.url,
            title: tab.title,
            start: now(),
            duration: 0,
            navigationEvents: [] // Navigation details store karne ke liye
        };
        
    } catch (e) {
        // Tab exists nahi karta (e.g., closed)
        console.warn("Could not start session for tab:", tabId, e);
    }
}

// 2. Session Khatam Karna aur Store Karna
function endSession(tabId, reason = "DEACTIVATED") {
    const s = activeTabData[tabId];
    if (!s) return;

    s.end = now();
    s.duration = s.end - s.start;
    s.endReason = reason;

    // Data ko 'logs' array mein store karo
    chrome.storage.local.get({ logs: [] }, data => {
        const logs = data.logs;
        logs.push(s);
        
        // **ACTIONABLE POINT:** Hum data ko trim nahi kar rahe hain
        // Aapko pura data chahiye toh trimming code hata diya hai.
        chrome.storage.local.set({ logs: logs }, () => {
            if (chrome.runtime.lastError) {
                 console.error("Storage error:", chrome.runtime.lastError);
            }
        });
    });
    delete activeTabData[tabId];
}

// === EVENT LISTENERS FOR DEEP LOGGING ===

// A. Tab Activation - Kaunsa tab focus mein aaya
chrome.tabs.onActivated.addListener(info => {
    // Pichle active tab ko end karo
    chrome.tabs.query({active: true, lastFocusedWindow: true}, function(tabs) {
        tabs.forEach(tab => {
            if (tab.id !== info.tabId) {
                endSession(tab.id, "SWITCHED_AWAY"); 
            }
        });
    });
    startSession(info.tabId);
});

// B. Tab Update - Same tab mein naya URL load hua
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // Agar tab update hua (url change, title change) toh pichla session end karo
    if (changeInfo.url) {
        endSession(tabId, "NAVIGATED_AWAY");
        startSession(tabId);
    }
});

// C. Tab Remove
chrome.tabs.onRemoved.addListener(tabId => endSession(tabId, "CLOSED"));

// D. Granular Web Navigation Events
// webNavigation.onCommitted, onCompleted, onErrorOccurred sabse zyada info dete hain
chrome.webNavigation.onCommitted.addListener(details => {
    // frameId === 0 ka matlab main frame (i.e., not an iframe)
    if (details.frameId === 0 && activeTabData[details.tabId]) {
        activeTabData[details.tabId].navigationEvents.push({
            event: "COMMITTED",
            time: now(),
            url: details.url,
            transitionType: details.transitionType // e.g., link, typed, reload
        });
    }
});

chrome.webNavigation.onCompleted.addListener(details => {
    if (details.frameId === 0 && activeTabData[details.tabId]) {
        activeTabData[details.tabId].navigationEvents.push({
            event: "COMPLETED",
            time: now(),
            url: details.url,
        });
    }
});

// E. History Logging (Actionable: Search Query)
// Jab koi item history mein add ho
chrome.history.onVisited.addListener(historyItem => {
    // **ACTIONABLE POINT:** Check if it's a search engine URL
    const searchMatch = historyItem.url.match(/(\?|&)q=([^&]+)/i);
    if (searchMatch) {
        const query = decodeURIComponent(searchMatch[2].replace(/\+/g, ' '));
        console.log(`Actionable: Search performed: ${query} at ${historyItem.url}`);
        // Aap isko bhi storage mein save kar sakte hain 'searchLogs' key ke under
    }
});


// F. Periodic Update (Duration Tracking)
// Jo sessions active hain, unki duration har 30s mein update karte rahenge
chrome.alarms.create("durationUpdate", { periodInMinutes: 0.5 }); // Har 30 seconds
chrome.alarms.onAlarm.addListener(alarm => {
    if (alarm.name === "durationUpdate") {
        for (const id in activeTabData) {
            // duration ko update karte raho taaki session end na hone par bhi data rahe
            activeTabData[id].duration = now() - activeTabData[id].start; 
        }
    }
});

// G. Window Focus/Blur Logging
// Chrome window active hai ya nahi
chrome.windows.onFocusChanged.addListener(windowId => {
    const status = windowId === chrome.windows.WINDOW_ID_NONE ? "BLURRED" : "FOCUSED";
    console.log(`Window Focus Change: ${status} at ${now()}`);
    // Aap isko bhi storage mein save karke overall chrome-active time track kar sakte hain
});