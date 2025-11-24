'use strict';

/*
Notes, since this is quite an ugly collection of functions that implement
	an automatically saving form with a dynamic number of fields

load functions will load the initial fields
	loadHotkeys makes some anonymous onchange functions that call saveOptions
	loadPresets() re-calculates the presets field, it's called on save too

saveOptions saves all the fields

consider hotkey_options as read-only, 
	it will be updated through saveOptions and re-applied in main.js

translate() should be called when we add new elements that need translation
*/

const api = typeof browser !== 'undefined' ? browser : chrome;

const TRANSFORM_FIELDS = ['scale_increment', 'rotate_increment', 'position_increment'];

window.addEventListener('load', () => {
	api.extension.isAllowedIncognitoAccess(loadIncognito);

	//extension gets reloaded so this is useless?
	//window.onfocus = () => {chrome.extension.isAllowedIncognitoAccess(loadIncognito);};

	const change_elements = document.querySelectorAll('.save_onchange');
	for (const elements of change_elements) {
		elements.onchange = saveOptions;
	}

	const keyup_elements = document.querySelectorAll('.save_oninput');
	for (const elements of keyup_elements) {
		elements.oninput = saveOptions;
	}

	//alt_disabled doesn't do anything on firefox, so hide it
	const disable_alt_select = document.getElementById('disable_alt');
	if (navigator.userAgent.indexOf('Firefox/') !== -1) {
		disable_alt_select.parentNode.parentNode.style.setProperty('display', 'none');
	}

	const preset_select = document.getElementById('preset');
	preset_select.onchange = checkReset;

	const reset_button = document.getElementById('reset');
	reset_button.onclick = reset;

	const add_button = document.getElementById('add');
	add_button.onclick = addRow;

	//set hotkey_options
	restore_options(() => {
		loadDisableAlt(hotkey_options['disable_alt']);
		loadAlwaysOn(hotkey_options['always_on']);
		loadPresets(hotkey_options['hotkeys'], hotkey_presets);
		loadHotkeys(hotkey_options['hotkeys']);
		loadTransformSettings(hotkey_options['transform_settings']);
	});
});

function loadTransformSettings(values) {
	for (const field of TRANSFORM_FIELDS) {
		const element = document.getElementById(field);
		element.value = values[field];
	}
}

function loadDisableAlt(new_disable_alt) {
	const disable_alt = document.getElementById('disable_alt');
	disable_alt.checked = new_disable_alt;
}

function checkReset(event) {
	const preset_select = document.getElementById('preset');
	const button = preset_select.parentNode.parentNode.getElementsByTagName('button')[0];

	//check to see if the current value is also a default preset
	if (preset_select.value !== checkPresets(hotkey_options['hotkeys'], hotkey_presets)) {
		//enable reset button if it's not
		button.disabled = false;
	} else {
		//disable it if matched
		button.disabled = true;
	}
}

function loadAlwaysOn(selected_mode) {
	const always_on_select = document.getElementById('always_on');

	//clear any options that might've been set
	always_on_select.textContent = '';

	for (const mode of always_on_modes) {
		let option = document.createElement('OPTION');
		option.value = mode;
		option.dataset.translate = `settings_${mode}`;

		if (selected_mode === mode) {
			option.selected = true;
		}

		always_on_select.add(option);
	}
}

function loadPresets(hotkeys, presets) {
	const preset_select = document.getElementById('preset');
	const preset_selected = checkPresets(hotkeys, presets);

	//clear previous values
	preset_select.textContent = '';

	for (const name of Object.keys(presets)) {
		let option = document.createElement('OPTION');
		option.dataset.translate = `settings_${name}`;
		option.value = name;

		if (name === preset_selected) {
			option.selected = true;
			const button = preset_select.parentNode.parentNode.getElementsByTagName('button')[0];
			button.disabled = true;
		}

		preset_select.add(option);
	}

	if (preset_selected === 'custom_hotkeys') {
		const custom_option = document.createElement('option');
		custom_option.dataset.translate = 'settings_custom_hotkeys';
		custom_option.value = 'custom_hotkeys';
		custom_option.selected = true;

		const preset_select = document.getElementById('preset');
		preset_select.add(custom_option);

		const button = preset_select.parentNode.parentNode.getElementsByTagName('button')[0];
		button.disabled = true;
	}
}

function loadHotkeys(hotkeys) {
	const commands = Object.keys(combined_functions);
	const hotkeys_table = document.getElementById('hotkeys').getElementsByTagName('tbody')[0];
	
	for (const hotkey of hotkeys) {
		const row = hotkeys_table.insertRow();

		const select_cell = row.insertCell();
		const select = document.createElement('SELECT');
		select.onchange = (event) => {
			//get hotkey input
			const hotkey_input = select.parentNode.parentNode.getElementsByTagName('INPUT')[0];
			
			//parse json
			let hotkey = JSON.parse(hotkey_input.dataset.hotkey)

			//update function_name
			hotkey['function_name'] = select.value;

			//save hotkey json
			hotkey_input.dataset.hotkey = JSON.stringify(hotkey);

			//if hotkey code is set we can save
			if (hotkey['code'] !== '') {
				saveOptions();
			}
		};
		
		for (const command of commands) {
			const option = document.createElement('OPTION');
			option.dataset.translate = `commands_${command}`;
			option.value = command;

			//select the correct function/command
			if (hotkey['function_name'] === command) {
				option.selected = true;
			}

			select.add(option);
		}
		select_cell.appendChild(select);

		const input_cell = row.insertCell();
		const input = document.createElement('INPUT');

		input.addEventListener('keydown', (event) => {
			event.preventDefault();
			event.stopPropagation();

			input.value = hotkeyText(event);

			//save json hotkey to dataset
			const input_function_name = input.parentNode.parentNode.getElementsByTagName('SELECT')[0].value;
			const input_hotkey = {function_name: input_function_name, code: event.code, ctrlKey: event.ctrlKey, altKey: event.altKey, shiftKey: event.shiftKey, metaKey: event.metaKey};
			input.dataset.hotkey = JSON.stringify(input_hotkey);
		});

		input.addEventListener('keyup', (event) => {
			event.preventDefault();
			event.stopPropagation();

			input.blur();
			saveOptions();
		});

		input.type = 'text';
		input.dataset.hotkey = JSON.stringify(hotkey);
		input.value = hotkeyText(hotkey);
		input_cell.appendChild(input);

		const delete_cell = row.insertCell();
		const delete_button = document.createElement('BUTTON');
		delete_button.onclick = deleteRow;
		delete_button.textContent = 'X';
		delete_cell.appendChild(delete_button);
	}

	//translate any added presets
	translate();
}

//saveOptions is called when always_on changes, when reset is clicked or when a hotkey is set, hotkey function changed, hotkey row deleted
function saveOptions() {
	let new_options = {};

	new_options['disable_alt'] = document.getElementById('disable_alt').checked;

	if (new_options['transform_settings'] === undefined) {
		new_options['transform_settings'] = {};
	}

	for (const field of TRANSFORM_FIELDS) {
		let value = document.getElementById(field).value;

		if (isNaN(value) || value == 0) {
			const message = chrome.i18n.getMessage(`settings_${field}`) + ' ' + chrome.i18n.getMessage('settings_error_bad_number');
			flashMessage('error', message);
			return;
		}

		//convert to number, careful not to set those settings to strings
		new_options['transform_settings'][field] = Number(value);
	}

	const always_on = document.getElementById('always_on').value;

	if (always_on_modes.includes(always_on)) {
		new_options['always_on'] = always_on
	} else {
		flashMessage('error', 'settings_error_always_on');
		return;
	}

	const hotkey_inputs = document.querySelectorAll('input[data-hotkey]');
	new_options['hotkeys'] = [];
	let hotkeys_used = [];
	for (const input of hotkey_inputs) {
		const hotkey = JSON.parse(input.dataset.hotkey);

		//validate hotkey not already set
		if (hotkeys_used.includes(hotkeyText(hotkey))) {
			const message = hotkeyText(hotkey) + ' ' + chrome.i18n.getMessage('settings_error_hotkey_duplicate');
			flashMessage('error', message);
			return;
		}

		//skip unset hotkey rows
		if (hotkey.function_name === false) {
			continue;
		}

		//validate function_name
		if (Object.keys(combined_functions).includes(hotkey.function_name) === false) {
			const message = chrome.i18n.getMessage('settings_error_bad_function');
			flashMessage('error', message);
			return;
		}

		hotkeys_used.push(hotkeyText(hotkey));
		new_options['hotkeys'].push(hotkey);
	}

	//update preset calculation
	loadPresets(new_options['hotkeys'], hotkey_presets);
	translate();

	//add preset calculation to options
	new_options['preset'] = document.getElementById('preset').value;

	//console.log('new:', new_options);
	save_options(new_options, () => {
		const message = chrome.i18n.getMessage('settings_saved');
		flashMessage('success', message);
	});
}

function flashMessage(type, message) {
	const delays = {success: 2000, warning: 2000, error: 5000};

	//remove old elements in case saves are done in quick succession
	const old_elements = document.querySelectorAll('div.alert-box');
	for (const old_element of old_elements) {
		old_element.remove();
	}

	//create and set new div, fade in
	const element = document.createElement('DIV');
	element.textContent = message;
	element.classList.add('alert-box');
	element.classList.add(type);
	element.classList.add('fade');
	document.body.appendChild(element);
	
	//after a delay, fade out
	setTimeout(function() {
	 	element.classList.remove('fade');
	}, delays[type]);
}

function hotkeyText(hotkey) {
	let result = '';

	if (hotkey.ctrlKey === true) {
		result += 'Ctrl + ';
	}

	if (hotkey.altKey === true) {
		result += 'Alt + ';
	}

	if (hotkey.shiftKey === true) {
		result += 'Shift + ';
	}

	if (hotkey.metaKey === true) {
		result += 'Meta + ';
	}

	result += hotkey.code;

	return result;
}

function checkPresets(current, presets) {
	let result = 'custom_hotkeys';

	//check to see if always on is default first...
	const always_on_select = document.getElementById('always_on');
	if (always_on_select.value === HOTKEY_DEFAULT['always_on']) {
	
		//iterate each preset
		for (const [name, hotkeys] of Object.entries(presets)) {

			//check each preset
			if (checkPreset(current, hotkeys) === true) {
				//found a matching preset, stop looking
				result = name;
				break;
			}
		}
	}

	return result;
}

function checkPreset(current, preset) {
	let result = true;

	//check length
	if (current.length === undefined || current.length <= 0 || current.length !== preset.length) {
		return false;
	}

	//iterate each hotkey in order
	for (let i = 0; i < preset.length; i++) {

		//check each hotkey field
		if (hotkeyText(current[i]) !== hotkeyText(preset[i]) || current[i].function_name !== preset[i].function_name) {
			//console.log('not eq', hotkeyText(current[i]), hotkeyText(preset[i]), current[i].function_name, preset[i].function_name);
			return false;
		} else {
			//console.log('eq', hotkeyText(current[i]), hotkeyText(preset[i]), current[i].function_name, preset[i].function_name);
		}
	}

	return result;
}

async function reset() {
	//get hotkey tbody
	const hotkeys_table = document.getElementById('hotkeys').getElementsByTagName('tbody')[0];

	//clear it
	hotkeys_table.textContent = '';

	//add back selected preset hotkeys
	const preset_select = document.getElementById('preset');
	const new_hotkeys = preset_select.value !== 'custom_hotkeys' ? hotkey_presets[preset_select.value] : hotkey_presets['default_hotkeys'];
	
	loadAlwaysOn(HOTKEY_DEFAULT['always_on']);
	loadHotkeys(new_hotkeys);
	saveOptions();
}

function addRow() {
	loadHotkeys([{function_name: false, code: ''}]);
}

function deleteRow() {
	this.parentNode.parentNode.remove();
	saveOptions();
}

function loadIncognito(allowed) {
	//get checkbox
	const incognito_checkbox = document.getElementById('incognito');

	if (allowed) {
		incognito_checkbox.checked = true;
	} else {
		incognito_checkbox.checked = false;
	}

	if (navigator.userAgent.indexOf('Firefox/') !== -1) {
		//firefox won't let us open the url so make this unclickable
		incognito_checkbox.disabled = true;
	}

	//set button onclick
	incognito_checkbox.onclick = () => {
		const url = 'chrome://extensions/?id=' + api.runtime.id;
		api.tabs.create({'url': url});
		return false;
	}
};