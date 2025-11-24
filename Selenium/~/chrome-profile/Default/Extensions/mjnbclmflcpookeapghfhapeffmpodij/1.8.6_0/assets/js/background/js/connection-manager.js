import ProxyController from "./proxy-control.js"
import Discovery from "./discovery.js"
import StateManager from "./state-manager.js"

export default class ConnectionManager {

	constructor() { }

	connect(tag) {
		chrome.storage.local.set({ "enabled": true }, function () {
			let discovery = new Discovery()
			discovery.getProxyController(function (controller) {
				controller.enable(function () {
					let stateManager = new StateManager()
					stateManager.set(tag);
				});
			})
		});
	}

	disconnect() {
		chrome.storage.local.set({ "enabled": false }, function () {
			let proxyController = new ProxyController()
			proxyController.disable(function () {
				let stateManager = new StateManager()
				stateManager.set("disconnect");
			});
		});
	};
}
