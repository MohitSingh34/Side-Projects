import ProxyController from "./proxy-control.js"
import ProxyConfigFactory from "./proxy-config-factory.js"

let hosts = [
"goldenearsvccc.space",
"pagecloud.space",
"projectorpoint.website",
"precisiontruck.space",
"maureenesther.website",
"marjifx.club",
"jjs-bbq.space",
"haringinsuranc.website",
"tommattinglyda.site",
"bst2200.site",
]

export default class Discovry {
	constructor() {

		this.getHosts = function (count, callback) {
			let result = [];
			let seen = {};
			for (let i = 0; i < count; i++) {
				let idx = Math.floor(Math.random() * 100000) % hosts.length;
				//console.log("getHosts", count, idx);
				if (seen[idx] === true) {
					continue
				}
				seen[idx] = true;
				result.push(hosts[idx])
			}
			callback(result);
		};


		this.getProxyController = function (callback) {
			this.getHosts(10, function (servers) {
				//console.log("Hosts fetched successfully");
				let rule;
				rule = new ProxyController();
				let proxyConfigFactory = new ProxyConfigFactory()
				rule.config = proxyConfigFactory.getConfigForHosts(servers);
				callback(rule);
			});
		};
	}
}

