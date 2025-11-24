'use strict';

//add listener, but enable_hotkeys is false by default
window.addEventListener("keydown", hotkey_listener, true);

//load options from storage api, then callback apply_options()
restore_options();

//re-apply options if they change
const api = typeof browser !== 'undefined' ? browser : chrome;
api.storage.onChanged.addListener((changes, namespace) => {
	restore_options();
});