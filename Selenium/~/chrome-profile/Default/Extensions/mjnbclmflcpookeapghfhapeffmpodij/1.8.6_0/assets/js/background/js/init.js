import ConnectionManager from "./connection-manager.js"
export default function init() {
	"use strict";
	chrome.storage.local.get(["runCount"], function (e) {
		let value = parseInt(e.runCount)
		let runCount = (value && value > 0 ? value : 0) + 1;
		chrome.storage.local.set({ 'runCount': runCount });
	});

	chrome.storage.local.get(["enableCount"], function (e) {
		let value = parseInt(e.enableCount)
		chrome.storage.local.set({ 'enableCount': (value && value > 0 ? value : 0) });
	});


	//chrome.proxy.settings.get({}, (x) => ga('send', 'event', 'level-of-control', x.levelOfControl));
}

