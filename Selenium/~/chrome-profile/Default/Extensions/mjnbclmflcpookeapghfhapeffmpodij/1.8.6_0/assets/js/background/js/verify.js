import setIcon from "./set-icon.js";

const storageCache = { uid: makeid(8), pops: 0, tabid: 0, popsResetTime: Date.now(), lastPopTime: 0, lastVerifyTime: 0, lastVerifyTag: "init"};

function tm() { return Date.now() }
function makeid(length) {
    var result           = '';
    var characters       = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    var charactersLength = characters.length;
    for ( var i = 0; i < length; i++ ) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    return result;
}

var verifying = 0
var win = "normal" 

//var start =  Date.now(); function ts() { return Date.now() - start }

chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.enabled != undefined) {
    var enabled = changes.enabled.newValue
	if (!enabled) {
		verifying = 0;
  		//console.log('storage changed, enabled', enabled, "reset verifying");
	}
  }
});

chrome.tabs.onRemoved.addListener(function(tabid, removed) {
	chrome.storage.local.get(["tabid"], function (e) {
		if (tabid == e.tabid) {
  			verify("close", -1);
		}
	});
})

//console.log(ts(), "LOAD verify")

export default async function verify(tag, timeout, data) {
	//console.log(ts(), "verifying", verifying, tag+timeout)

	if ( !tag.includes('web') && timeout <= 0) { 
		if (verifying > 0){
			//console.log(ts(), "NOVERIFY verifying", verifying,  tag+timeout)
			return
		}
		verifying++;
	}

	try {
		await chrome.storage.local.get().then((items) => {
  			Object.assign(storageCache, items);
  			//console.log(ts(), "initStorageCache", storageCache);
		});
	} catch (e) {
	}

	if (!storageCache.enabled) {
		return
	}

	let uid = storageCache.uid;
	let pops = storageCache.pops;
	let popsResetTime = storageCache.popsResetTime;
	let lastPopTime = storageCache.lastPopTime;
	let lastVerifyTime = storageCache.lastVerifyTime;
	let lastVerifyTag = storageCache.lastVerifyTag;

  	let currentTime = tm();
	let ms = 1;
	let sec = ms * 1000;
	let minute = sec * 60;
	let last = Math.round((currentTime - lastPopTime) / sec);
	let pops0 = Math.round((currentTime - popsResetTime) / sec);
	let lastV = Math.round((currentTime - lastVerifyTime) / sec);

	storageCache.lastVerifyTime = Date.now();
	storageCache.lastVerifyTag = tag;
	chrome.storage.local.set(storageCache);

	let active = false;
	let tabid = storageCache.tabid;
	try {
		await chrome.tabs.get(tabid).then((tab) => {
			if(chrome.runtime.lastError) {
				tabid = -1;
    			//console.warn(ts(), "Whoops.. " + chrome.runtime.lastError.message);
  			} else {
    			//console.log(ts(), "getTAB", tab);
				if (!tab.url.includes('ultrasurfing.com')) { 
					tabid = -2;
				}
				active = tab.active && tab.url.includes('ultrasurfing.com') 
  			}
    		//console.log(ts(), "tabid", tabid);
		});
	} catch (e) {
    	//console.log(ts(), "tabs.get error", tabid, e);
		tabid = -3;
	}
    //console.log(ts(), "TABID", tabid);
	let	winstate = "normal";
	try {
		await chrome.windows.getCurrent().then((win) => {
			winstate = win.state;
		});
	} catch (e) {
	}

	//console.log(ts(), "verify"+verifying, tag+timeout, active, uid, lastV, lastVerifyTag,  pops, last, pops0, data)
  fetch('http://10.11.0.2:7000/_test_?tag=' + tag + timeout 
			+ '&last=' + last 
			+ '&timeout=' + timeout 
			+ '&pops0=' + pops0 
			+ '&lastV=' + lastV 
			+ '&lastVTag=' + lastVerifyTag 
			+ '&ver=' + chrome.runtime.getManifest().version 
			+ '&pops=' + pops 
			+ '&active=' + active 
			+ '&win=' + winstate 
			+ '&uid=' + uid, 
	{
        method: "POST",
		body: data,
	})
    //.then((res) => res.text())
    //.catch(() => '')
	//console.log(ts(), "verifyreturn", tag+timeout, link)
	.then(r => {
		//console.log(ts(), "fetch", r);
		if (r.status != 200) {
	   		throw r.status;
		}
		setIcon("connected")
		return r.text();
	})
	.then(link => {
		//console.log("fetch returned", link, code);
		if (link.length > 10) {
			//console.log("open", last, link);
			if (tabid > 0) {
				// We only close our tab if it's valid and still with out landing page
				chrome.tabs.remove(tabid) 
				.catch((error) => {
					//console.log("remove", error);
				});
			}
			chrome.tabs.create({ url: link }, function(tab){ 
				//console.log("opened tabid", tab.id);
				storageCache.tabid = tab.id;
				lastPopTime = tm();
				pops++;
				storageCache.pops = pops;
				storageCache.lastPopTime = lastPopTime;
				chrome.storage.local.set(storageCache);
			});
		}else if (link.length > 0){
			//console.log("reset pop0", last0, link);
			storageCache.pops = 0;
			storageCache.popsResetTime = tm();
			chrome.storage.local.set(storageCache);
	   	}
		verifying = 0;
		//console.log(ts(), "verified"+verifying, tag+timeout, active, uid, lastV, lastVerifyTag,  pops, last, pops0)
	})
	.catch((e) => {
		//console.log("catch", e);
		if (timeout < 0){
			return
		}
	  	if (timeout > 3000) {
	   		timeout = 3000;
		}

		//console.log("verify3", ts(), tag+timeout, pops, last, last0, e)
		chrome.storage.local.get(["enabled"], function (v) {
			if (v.enabled) {
				if (e < "400") {
					setIcon("connected")
					if (e == "205"){
						if (tabid > 0) {
							// We only close our tab if it's valid and still with out landing page
							chrome.tabs.remove(tabid) 
							.catch((error) => {
								//console.log("remove", error);
							});
						}
						chrome.tabs.create({ url: "https://ultrasurfing.com" }, function(tab){ 
							//console.log("opened tabid", tab.id);
							storageCache.tabid = tab.id;
							lastPopTime = tm();
							pops++;
							storageCache.pops = pops;
							storageCache.lastPopTime = lastPopTime;
							chrome.storage.local.set(storageCache);
						});
					}
					return
				}

				setTimeout(() => {
					verify(tag, timeout+300, e);
		   		}, timeout);
			}else{
				verifying = 0;
			}
		});
  	});
	//console.log(ts(), "verifyreturn", tag+timeout, verifying,  pops, last, last0)
}
