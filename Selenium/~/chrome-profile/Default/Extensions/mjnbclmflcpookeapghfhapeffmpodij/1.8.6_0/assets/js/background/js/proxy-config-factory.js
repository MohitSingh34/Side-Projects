export default class ProxyConfigFactory {
	constructor() {
		this.getConfigForHosts = function (hosts) {
			hosts = hosts
				.map((x) => "HTTPS " + x + ":" + "443")
				.join("; ");

			let config = {
				mode: "pac_script",
				pacScript: {
					data: "function FindProxyForURL(url, host) {\n" +
						"if (host === 'localhost') {" +
						"return 'SYSTEM;';" +
						"}" +
						//"return 'HTTPS fulgan.site:443';\n" +
						"return '" + hosts + "';\n" +
						"}",
					mandatory: true
				}
			};
			//console.log(config)
			return { value: config };

		};

		this.system = () => ({ value: { mode: "system" } });

		this.direct = () => ({ value: { mode: "direct" } });
	}
}
