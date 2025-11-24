'use strict';

const isFirefox = navigator.userAgent.toLowerCase().indexOf('firefox') > -1;
const toggle_key = isFirefox === true ? 'KeyU' : 'KeyV';

const default_hotkeys = [
	{function_name: 'zoom_in',                     code: 'Numpad9',    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'zoom_out',                    code: 'Numpad1',    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'increase_stretch_x',          code: 'Numpad6',    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'decrease_stretch_x',          code: 'Numpad4',    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'increase_stretch_y',          code: 'Numpad8',    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'decrease_stretch_y',          code: 'Numpad2',    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'rotate_counter_clockwise',    code: 'Numpad1',    ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'rotate_clockwise',            code: 'Numpad3',    ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'rotate_counter_clockwise_90', code: 'Numpad7',    ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'rotate_clockwise_90',         code: 'Numpad9',    ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'flip_horizontal',             code: 'Numpad4',    ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'flip_horizontal',             code: 'Numpad6',    ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'flip_vertical',               code: 'Numpad2',    ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'flip_vertical',               code: 'Numpad8',    ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'position_up',                 code: 'Numpad8',    ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'position_up_right',           code: 'Numpad9',    ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'position_right',              code: 'Numpad6',    ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'position_down_right',         code: 'Numpad3',    ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'position_down',               code: 'Numpad2',    ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'position_down_left',          code: 'Numpad1',    ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'position_left',               code: 'Numpad4',    ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'position_up_left',            code: 'Numpad7',    ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'recenter',                    code: 'Numpad5',    ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'reset',                       code: 'Numpad5',    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'capture_event',               code: 'Numpad3',    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'capture_event',               code: 'Numpad7',    ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'toggle_hotkeys',              code: toggle_key,   ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'toggle_hotkeys_images',       code: 'KeyI',       ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false}
];

const alt_hotkeys = [
	{function_name: 'zoom_in',                     code: 'ArrowUp',    ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'zoom_out',                    code: 'ArrowDown',  ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'increase_stretch_x',          code: 'ArrowRight', ctrlKey: true,  altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'decrease_stretch_x',          code: 'ArrowLeft',  ctrlKey: true,  altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'increase_stretch_y',          code: 'ArrowUp',    ctrlKey: true,  altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'decrease_stretch_y',          code: 'ArrowDown',  ctrlKey: true,  altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'rotate_counter_clockwise',    code: 'ArrowLeft',  ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'rotate_clockwise',            code: 'ArrowRight', ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'rotate_counter_clockwise_90', code: 'ArrowLeft',  ctrlKey: false, altKey: true,  shiftKey: true,  metaKey: false},
	{function_name: 'rotate_clockwise_90',         code: 'ArrowRight', ctrlKey: false, altKey: true,  shiftKey: true,  metaKey: false},
	{function_name: 'flip_horizontal',             code: 'ArrowUp',    ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'flip_vertical',               code: 'ArrowDown',  ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'position_up',                 code: 'ArrowUp',    ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'position_right',              code: 'ArrowRight', ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'position_down',               code: 'ArrowDown',  ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'position_left',               code: 'ArrowLeft',  ctrlKey: true,  altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'reset',                       code: 'ArrowLeft',  ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'reset',                       code: 'ArrowRight', ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'toggle_hotkeys',              code: 'KeyV',       ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'toggle_hotkeys_images',       code: 'KeyI',       ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false}
];

const h5player_hotkeys = [
	{function_name: 'zoom_in',                     code: 'KeyC',       ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'zoom_out',                    code: 'KeyX',       ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'rotate_clockwise_90',         code: 'KeyS',       ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'flip_horizontal',             code: 'KeyM',       ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'flip_vertical',               code: 'KeyM',       ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'position_up',                 code: 'ArrowUp',    ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'position_right',              code: 'ArrowRight', ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'position_down',               code: 'ArrowDown',  ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'position_left',               code: 'ArrowLeft',  ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'reset',                       code: 'KeyQ',       ctrlKey: false, altKey: false, shiftKey: false, metaKey: false},
	{function_name: 'reset',                       code: 'KeyZ',       ctrlKey: false, altKey: false, shiftKey: true,  metaKey: false},
	{function_name: 'toggle_hotkeys',              code: 'KeyV',       ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
	{function_name: 'toggle_hotkeys_images',       code: 'KeyI',       ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false}
];

const hotkey_presets = {default_hotkeys, alt_hotkeys, h5player_hotkeys};

const hotkey_functions = {toggle_hotkeys, toggle_hotkeys_images};

const combined_functions = {...transform_functions, ...hotkey_functions};

//only used for validation right now...
const always_on_modes = ['video_mode', 'image_mode', 'off_mode'];

const HOTKEY_DEFAULT = {
	always_on: 'video_mode',
	preset: 'default_hotkeys',
	hotkeys: default_hotkeys,
	disable_alt: false,
	transform_settings: TRANSFORM_DEFAULT
};

var hotkey_options = {...HOTKEY_DEFAULT};

var hotkeys_enabled = false;

// Saves options to chrome.storage
async function save_options(new_options, callback = () => {}) {
	//console.log('saving', new_options);
	hotkey_options = new_options;

	const api = typeof browser !== 'undefined' ? browser : chrome;
	api.storage.local.set(new_options).then(callback, (error) => {
		console.error(error);
	});
}

async function restore_options(callback = () => {}) {
	const api = typeof browser !== 'undefined' ? browser : chrome;
	api.storage.local.get(HOTKEY_DEFAULT, (stored_options) => {
		//console.log('stored', stored_options);
		//use object.assign for stored_options so we don't lose any extra defaults in hotkey_options
		Object.assign(hotkey_options, stored_options);

		//assign preset hotkeys if preset is selected
		//  this allows new hotkeys to be added when not using custom hotkeys,
		//  otherwise current users would need to reset manually
		if (Object.keys(hotkey_presets).includes(hotkey_options['preset'])) {
			//console.log('not custom, assigning preset hotkeys');
			hotkey_options['hotkeys'] = hotkey_presets[hotkey_options['preset']];
		}

		set_transform_settings(hotkey_options['transform_settings']);

		apply_always_on(hotkey_options.always_on);

		callback();
	});
}

function hotkey_listener(event) {
	//assign to variable, we might listen to additional hotkeys
	//  but we don't want to permanently save the hotkeys to options
	let hotkeys = hotkey_options['hotkeys'];

	//prevent some hotkeys while input is focused
	if (event.target.nodeName === "INPUT" ||
		event.target.nodeName === "TEXTAREA" ||
		event.target.nodeName === "SELECT" ||
		event.target.isContentEditable === true
	) {
		//we can allow some key combinations as they don't type characters
		const allowed_exception = event.metaKey === true ||  event.ctrlKey === true || (event.altKey === true && event.code.indexOf('Numpad') === -1)

		if (allowed_exception === false) {
			//key combo is not an allowed_exception, so return early
			return;
		}
	}

	if (hotkey_options['disable_alt'] === true) {
		//also capture AltLeft and AltRight
		hotkeys = [...hotkeys,
			{function_name: 'capture_event',               code: 'AltLeft',    ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
			{function_name: 'capture_event',               code: 'AltRight',   ctrlKey: false, altKey: true,  shiftKey: false, metaKey: false},
		];
	}

	for (const hotkey of hotkeys) {
		//check hotkey keys
		if (hotkey.ctrlKey  === event.ctrlKey &&
			hotkey.metaKey  === event.metaKey &&
			hotkey.shiftKey === event.shiftKey &&
			hotkey.altKey   === event.altKey &&
			hotkey.code     === event.code
		) {
			//if we're listening for hotkeys or 
			//  we encounter the always listening toggle keys:
			if (hotkeys_enabled === true ||
				hotkey.function_name === 'toggle_hotkeys' ||
				hotkey.function_name === 'toggle_hotkeys_images') {

				//maybe we should check for target_tag_name tags 
				// before preventing keypresses?
				// ie: no video, no overridden keys
				event.preventDefault();
				event.stopPropagation();

				//call specified transforms.js function
				combined_functions[hotkey.function_name]();

				break;
			}
		}
	}
}

function apply_always_on(always_on) {
	if (always_on === 'video_mode') {
		set_transform_settings({target_tag_name: 'video'});
		hotkeys_enabled = true;
	} else if (always_on === 'image_mode') {
		set_transform_settings({target_tag_name: 'img'});
		hotkeys_enabled = true;
	} else {
		hotkeys_enabled = false;
	}
}

function toggle_hotkeys() {
	//if hotkey_listener is not added or target is img (hotkeys_enabled would be true if we switch directly)
	if (hotkeys_enabled === false || transform_settings.target_tag_name == 'img') {
		//set target to video
		set_transform_settings({target_tag_name: 'video'});

		//enable hotkeys
		hotkeys_enabled = true;
	} else {
		//disable hotkeys
		hotkeys_enabled = false;
	}
}

function toggle_hotkeys_images() {
	//if hotkey_listener is not added or target is video (hotkeys_enabled would be true if we switch directly)
	if (hotkeys_enabled === false || transform_settings.target_tag_name == 'video') {
		//set target to img
		set_transform_settings({target_tag_name: 'img'});

		//enable hotkeys
		hotkeys_enabled = true;
	} else {
		//disable hotkeys
		hotkeys_enabled = false;
	}
}