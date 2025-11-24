var enabled;
var state;
chrome.storage.local.get(["enabled", "state"], function (e) {
    enabled = e.enabled;
    state = e.state;
});

chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local') {
        if (changes.enabled != undefined) {
            enabled = changes.enabled.newValue
            //console.log('storage enabled', enabled);
        } else if (changes.state != undefined) {
            state = changes.state.newValue
            //console.log('storage state', state);
        }
    }
})

var extensionInterface = angular.module('extensionInterface', []);

extensionInterface.factory('extensionInfo', function () {
    var getReviewPage, getExtensionPage;
    getExtensionPage = function (id) {
        id = typeof id === 'string' ? id : chrome.runtime.id;
        return "https://chrome.google.com/webstore/detail/" + id;
    };
    getReviewPage = function (id) {
        return getExtensionPage(id) + "/reviews"
    };
    return {
        getExtensionPage: getExtensionPage,
        getReviewPage: getReviewPage
    };
});

extensionInterface.factory('changeTracker', ['$interval', function ($interval) {
    var result;
    result = {
        onStatusChange: function () {
        },
        onStateChange: function () {
        },
        status: enabled,
        state: state
    };
    $interval(function () {
        if (state !== result.state) {
            result.state = state;
            try {
                result.onStateChange(result.state);
            } catch (e) {
            }
        }
        if (enabled !== result.status) {
            result.status = enabled;
            try {
                result.onStatusChange(result.status);
            } catch (e) {
            }
        }
    }, 200);
    return result;
}]);

extensionInterface.factory('extensionState', ['changeTracker', function (changeTracker) {
    var result, callbackList;
    callbackList = [];
    result = {
        state: state,
        onChange: function (callback) {
            callbackList.push(callback);
        }
    };
    changeTracker.onStateChange = function (state) {
        result.state = state;
        for (var i = 0; i < callbackList.length; i++) {
            try {
                callbackList[i](result.state);
            } catch (e) {
            }

        }
    };
    return result;
}]);

extensionInterface.factory('extensionStatus', ['changeTracker', function (changeTracker) {
    var result, callbackList;
    callbackList = [];
    result = {
        status: enabled,
        onChange: function (callback) {
            callbackList.push(callback);
        }
    };
    changeTracker.onStatusChange = function (status) {
        result.status = status;
        for (var i = 0; i < callbackList.length; i++) {
            try {
                callbackList[i](result.status);
            } catch (e) {
            }

        }
    };
    return result;
}]);

extensionInterface.factory('controlExtension', [function () {
    return {
        enable: function () {
            chrome.runtime.sendMessage({ user: "connect" });
            chrome.storage.local.get(["enableCount"], function (e) {
                let value = parseInt(e.enableCount);
                chrome.storage.local.set({ 'enableCount': (value && value > 0 ? value : 0) + 1 });
            });
        },
        disable: function () {
            chrome.runtime.sendMessage({ user: "disconnect" });
        }
    };
}]);