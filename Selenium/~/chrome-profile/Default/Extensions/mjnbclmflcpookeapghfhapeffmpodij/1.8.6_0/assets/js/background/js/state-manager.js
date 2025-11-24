import setIcon from "./set-icon.js"
import verify from "./verify.js"

//var start =  Date.now(), function ts() { return Date.now() - start }

export default class StateManager {
	constructor() {
		this.set = function (state) {
    		chrome.storage.local.get(["enabled"], function (e) {
		    	state = e.enabled === true || state === "conflict" ? state : "disconnect";
		    	//console.log(ts(), "Setting state:", e.enabled, state);
		    	switch (state) {
		    	    case "start":
		    	    case "open":
		    	    case "load":
		    	        setSuccess(state);
		    	        break;
		    	    case "disconnect":
		    	        setDisconnect(state);
		    	        break;
		    	    default:
		    	        //console.warn("state-manager.set() State not recognized", state);
		    	}
    		});
		};
		
		
		let setSuccess = function (event) {
		    //console.log(ts(), "setSuccess", event);
		    updateStatus("success");
			setIcon("connecting");
			verify(event, 0);
		};
		let setDisconnect = function (event) {
		    updateStatus(event);
		    //console.log("setDisconnect:", event);
			setIcon("ready")
		};
	
	}
}
function updateStatus(s) { 
	chrome.storage.local.set({'state': s}); 
}
