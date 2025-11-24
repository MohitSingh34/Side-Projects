'use strict';

//these scales assume the device is 16:9
const SCALE_16_10 = (16/9) / (16/10);
//this may not be perfect for all UW 21:9 res
const SCALE_21_9 = 1.33;

//Note: if default increments change, 
// messages.json defaults need to be updated too
var TRANSFORM_DEFAULT = {
	target_tag_name: 'video',
	scale_increment:       5,
	rotate_increment:      5,
	position_increment:   20
}

var transform_settings = {...TRANSFORM_DEFAULT};

//constant default transform values
const DEFAULT = {
	left:       0,
	top:        0,
	rotate:     0,
	rotate_y:   0,
	scale:    1.0,
	scale_x:  1.0,
	scale_y:  1.0
};

//remember current values
var current = {...DEFAULT};
var stylesheet =      null;

function transformed() {
	let result = true;

	if (JSON.stringify(current) === JSON.stringify(DEFAULT)) {
		result = false;
	}

	return result;
}

//call this before doing any transforms
function set_transform_settings(new_transform_settings) {
	if (stylesheet === null) {
		stylesheet = document.createElement('STYLE');
		document.head.appendChild(stylesheet);
	}

	//temporarily store the old target to see if it changes
	let old_target_tag_name = transform_settings.target_tag_name;

	//add or replace new settings
	Object.assign(transform_settings, new_transform_settings);

	//reset if target changes
	if (old_target_tag_name !== transform_settings.target_tag_name) {
		reset();
	}
}

//Note: we only match the first video for vertical_scale aspect ratio...
function vertical_scale() {
	let result = current.scale;

	//only vertically scale videos
	if (transform_settings.target_tag_name !== 'video') {
		return DEFAULT.scale;
	}

	//iterate target elements
	let target_elements = document.getElementsByTagName(transform_settings.target_tag_name);
	for (const element of target_elements) {
		//rescale, *dependent* on video aspect ratio
		//beware, current.rotate has already changed at this point...

		//horizontal to vertical
		if (current.rotate % 180 === 0) {
			//don't set scale to NaN on accident / div by zero
			if (element.videoHeight !== 0 && element.videoWidth !== 0) {
				result = element.videoHeight / element.videoWidth;
				break;
			}
		//vertical to horizontal
		} else if (current.rotate % 90 === 0) {
			result = DEFAULT.scale;
			break;
		}
	}

	return result;
}

function transform(new_values = {}, rescale_vertical = false) {
	//use new values if set, otherwise use current values
	Object.assign(current, new_values);

	let transform = '';
	transform += ` translate(${current.left}px, ${current.top}px) `;
	transform += ` rotate(${current.rotate}deg) `;
	transform += ` rotateY(${current.rotate_y}deg) `;
	transform += ` scale(${current.scale}) `;
	transform += ` scaleX(${current.scale_x}) `;
	transform += ` scaleY(${current.scale_y}) `;
	//fix fullscreen transforms (chrome hardware acceleration bug?)
	transform += ` rotateZ(0.000001deg) `;

	let style_content = '';
	style_content += `${transform_settings.target_tag_name} {`;
	style_content += ` transform-origin: center !important;`;
	style_content += ` transform: ${transform} !important;`;
	style_content += `}`;

	//set style
	stylesheet.textContent = style_content;
}

//rotate counter clockwise
function rotate_counter_clockwise() {
	const rotate = current.rotate - transform_settings.rotate_increment;
	transform({rotate});
}

//rotate clockwise
function rotate_clockwise() {
	const rotate = current.rotate + transform_settings.rotate_increment;
	transform({rotate});
}

//rotate counter clockwise 90
function rotate_counter_clockwise_90() {
	const rotate = current.rotate - 90;
	const scale = vertical_scale();
	transform({rotate, scale});
}

//rotate clockwise 90
function rotate_clockwise_90() {
	const rotate = current.rotate + 90;
	const scale = vertical_scale();
	transform({rotate, scale});
}

//flip left to right
function flip_horizontal() {
	const rotate_y = current.rotate_y + 180;
	transform({rotate_y});
}

//flip up to down
function flip_vertical() {
	const rotate = current.rotate + 180;
	const rotate_y = current.rotate_y + 180;
	transform({rotate, rotate_y});
}

//position up
function position_up() {
	let top = current.top - transform_settings.position_increment;
	transform({top});
}

//position up+right
function position_up_right() {
	let left = current.left + transform_settings.position_increment;
	let top = current.top - transform_settings.position_increment;
	transform({left, top});
}

//position right
function position_right() {
	let left = current.left + transform_settings.position_increment;
	transform({left});
}

//position down+right
function position_down_right() {
	let left = current.left + transform_settings.position_increment;
	let top = current.top + transform_settings.position_increment;
	transform({left, top});
}

//position down
function position_down() {
	let top = current.top + transform_settings.position_increment;
	transform({top});
}

//position down+left
function position_down_left() {
	let left = current.left - transform_settings.position_increment;
	let top = current.top + transform_settings.position_increment;
	transform({left, top});
}

//position left
function position_left() {
	let left = current.left - transform_settings.position_increment;
	transform({left});
}

//position up+left
function position_up_left() {
	let left = current.left - transform_settings.position_increment;
	let top = current.top - transform_settings.position_increment;
	transform({left, top});
}

function snap_scale(target, new_scale, increment) {
	let result_scale = new_scale;

	//if we're crossing the target boundary  or to 1/2 of an increment away
	if (Math.abs(target - new_scale) < increment / 2) {
		//snap to the target scale
		result_scale = target;
	}

	return result_scale;
}

//increase stretch on x-axis
function increase_stretch_x() {
	const increment = current.scale_x * transform_settings.scale_increment / 100;
	let scale_x = current.scale_x + increment;

	scale_x = snap_scale(DEFAULT.scale_x, scale_x, increment);
	scale_x = snap_scale(SCALE_16_10, scale_x, increment);

	transform({scale_x});
}

//decrease stretch on x-axis
function decrease_stretch_x() {
	const increment = current.scale_x * transform_settings.scale_increment / 100;
	let scale_x = current.scale_x - increment;

	scale_x = snap_scale(DEFAULT.scale_x, scale_x, increment);
	scale_x = snap_scale(SCALE_16_10, scale_x, increment);

	transform({scale_x});
}

//increase stretch on y-axis
function increase_stretch_y() {
	const increment = current.scale_y * transform_settings.scale_increment / 100;
	let scale_y = current.scale_y + increment;

	scale_y = snap_scale(DEFAULT.scale_y, scale_y, increment);
	scale_y = snap_scale(SCALE_21_9, scale_y, increment);

	transform({scale_y});
}

//decrease stretch on y-axis
function decrease_stretch_y() {
	const increment = current.scale_y * transform_settings.scale_increment / 100;
	let scale_y = current.scale_y - increment;

	scale_y = snap_scale(DEFAULT.scale_y, scale_y, increment);
	scale_y = snap_scale(SCALE_21_9, scale_y, increment);

	transform({scale_y});
}

function zoom_in() {
	const increment = current.scale * transform_settings.scale_increment / 100;
	let scale = current.scale + increment;

	scale = snap_scale(DEFAULT.scale, scale, increment);

	transform({scale});
}

function zoom_out() {
	const increment = current.scale * transform_settings.scale_increment / 100;
	let scale = current.scale - increment;

	scale = snap_scale(DEFAULT.scale, scale, increment);

	transform({scale});
}

//recenter
function recenter() {
	transform({left: 0, top: 0});
}

//reset all transformations
function reset() {
	transform(DEFAULT, false);
}

//override chrome hotkey control + 5 and youtube hotkeys
function capture_event() {
	//this captures the keys so they don't propagate, etc
}

const transform_functions = {
	zoom_in,
	zoom_out,
	increase_stretch_x,
	decrease_stretch_x,
	increase_stretch_y,
	decrease_stretch_y,
	rotate_counter_clockwise,
	rotate_clockwise,
	rotate_counter_clockwise_90,
	rotate_clockwise_90,
	flip_horizontal,
	flip_vertical,
	position_up,
	position_up_right,
	position_right,
	position_down_right,
	position_down,
	position_down_left,
	position_left,
	position_up_left,
	recenter,
	reset,
	capture_event
}