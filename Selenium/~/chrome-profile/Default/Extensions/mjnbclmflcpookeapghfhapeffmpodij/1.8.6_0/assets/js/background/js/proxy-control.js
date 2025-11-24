export default class ProxyController {
	constructor() {
		this.enable = function (callback) {
			//console.log("Proxy:", this.config);
			chrome.proxy.settings.set(this.config, function () {
				if (typeof (callback) === "function") {
					callback(true);
				}
			});
		};
		this.disable = function (callback) {
			chrome.proxy.settings.clear({}, function () {
				if (typeof (callback) === "function") {
					callback(true);
				}
			});
		};

	}
}
