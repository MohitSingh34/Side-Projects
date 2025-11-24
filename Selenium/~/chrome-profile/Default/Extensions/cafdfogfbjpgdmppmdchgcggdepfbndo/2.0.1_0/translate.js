function translate() {
	const elements = document.querySelectorAll('[data-translate]');

	//should I check for whether the elements textContent or innerhtml is blank?
	//const start_time = performance.now();
	for(const element of elements) {
		let translation = chrome.i18n.getMessage(element.dataset.translate);

		//chrome/firefox/edge special case Incognito/Private Browsing/InPrivate:
		if (element.dataset.translate === 'settings_incognito') {
			let incognito_term = chrome.i18n.getMessage('settings_incognito_chrome');
			if (navigator.userAgent.indexOf('Firefox/') !== -1) {
				incognito_term = chrome.i18n.getMessage('settings_incognito_firefox');
			} else if (navigator.userAgent.indexOf('Edg/') !== -1) {
				incognito_term = chrome.i18n.getMessage('settings_incognito_edge');
			}

			translation += ' ' + incognito_term;
		}	

		if (translation === '') {
			console.error(`Could not find translation for: ${element.dataset.translate}`);
			element.textContent = element.dataset.translate;
		} else if (element.dataset.translateType === 'label') {
			const label = document.createElement('LABEL');
			label.textContent = translation;
			let input_id = element.dataset.translate.substring(element.dataset.translate.indexOf('_') + 1);
			label.setAttribute('for', input_id);
			element.textContent = '';
			element.appendChild(label);
		} else {
			element.textContent = translation;
		}
	}
	//const total_time = performance.now() - start_time;
	//console.log('Translated in:', total_time);
}