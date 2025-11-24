chrome.commands.onCommand.addListener((command) => {
	//console.log(`Command "${command}" triggered`);
	
	if (command === "reload") {
		//even though runtime.reload is called after tabs.reload,
		//the reloaded tab will run the reloaded extension!
		//(tabs.reload can't be called after runtime.reload because
		//  the extension instantly stops then starts reloading)

		//reload the tab, 
		//file:/// still require a manual refresh
		chrome.tabs.reload();

		//reload the extension
		chrome.runtime.reload();
	}
});

// Check whether new version is installed
chrome.runtime.onInstalled.addListener(function(details){
	const api = typeof browser !== 'undefined' ? browser : chrome;
	const thisVersion = api.runtime.getManifest().version;
	const previousVersion = details.previousVersion;

    if (details.reason === "install"){
		api.runtime.openOptionsPage();
    // } else if (details.reason === "update" && "2.0.0" > previousVersion) {
	// 	api.storage.sync.get({alt_enabled: false}).then((result) => {
	// 		//if enabled, set preset
	// 		if (result['alt_enabled'] === true) {
	// 			api.storage.local.set({preset:'alt_hotkeys'}).then(() => {
	// 				//open settings after setting preset
	// 				api.runtime.openOptionsPage();
	// 			});
				
	// 			//then remove alt_enabled
	// 			api.storage.sync.remove('alt_enabled');
	// 		} else {
	// 			//otherwise, just open settings
	// 			api.runtime.openOptionsPage();
	// 		}
	// 	});
    }
});

// function open_page(path) {
//    chrome.tabs.create({'url': chrome.runtime.getURL(path)});
// }