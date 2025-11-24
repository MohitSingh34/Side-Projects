translate();

let store_url = 'https://chrome.google.com/webstore/detail/video-transformer/cafdfogfbjpgdmppmdchgcggdepfbndo';

if (navigator.userAgent.indexOf('Firefox/') !== -1) {
    store_url = 'https://addons.mozilla.org/en-US/firefox/addon/video-transformer/';
} else if (navigator.userAgent.indexOf('Edg/') !== -1) {
    store_url = 'https://microsoftedge.microsoft.com/addons/detail/video-transformer/ebfmnheipelagbcnlcmipdcenfccbfbp';
}

const settings_button = document.getElementById('settings');
settings_button.onclick = () => {window.open(chrome.runtime.getURL("settings.html"));};

const store_button = document.getElementById('store');
store_button.onclick = () => {window.open(store_url)};

const homepage_button = document.getElementById('homepage');
homepage_button.onclick = () => {window.open('https://xifer-web.appspot.com');};