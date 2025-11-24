//fix transformations getting applied to subsequent videos in YouTube
if (window.location.href.indexOf('www.youtube.com') !== -1) {
	let youtube_loaded = false;

	window.addEventListener('yt-page-data-updated', () => {
		if (youtube_loaded === false) {
			//youtube loaded a video
			youtube_loaded = true;
		} else {
			//reset on new videos
			reset();
		}
	});
}

if (isDirectVideoUrl() === true) {
	//onload
	window.addEventListener('load', (event) => {
		const video = document.querySelector('video');
		
		if (video) {
			//maximize width/height for file:/// videos, so that transformations work
			document.body.setAttribute('class', 'video-transformer-direct-fix');

			//add double-click full-screening, allows us to perform transformations in fullscreen
			document.addEventListener("dblclick", (event) => {
				event.preventDefault();
				event.stopPropagation();

				//requestFullscreen requires an event but
				// looks like the shadowDom gets there first when we dblclick on a video :(
				// so we'll only requestFullscreen when html element is double-clicked
				if (event.target.tagName !== 'VIDEO' && document.fullscreenElement === null) {
					document.body.requestFullscreen();
				} else if (document.fullscreenElement !== null) {
					document.exitFullscreen();
				}
			});
		}
	});
}

function isDirectVideoUrl() {
	const extensions = ['.mp4', '.webm'];

	for (const extension of extensions) {
		//if extension found in the location
		if (window.location.href.indexOf(extension) !== -1) {
			//if extension is at the end of the location
			if (window.location.href.length - window.location.href.indexOf(extension) === extension.length) {
				return true;
			}
		}
	}

	return false;
}

if (window.location.href.indexOf('www.douyu.com') !== -1) {
	//maybe not the cleanest fix for non-standard resolutions... 
	// video gets moved to the top, not centered vertically
	window.addEventListener('load', () => {
		const video = document.querySelector('video');

		if (video) {
			//remove all the crazy important top, left, transform css
			video.classList = '';
		}
	});
}