var enableDisableSwitch = angular.module('enableDisableSwitch', ['frapontillo.bootstrap-switch', 'extensionInterface']);

enableDisableSwitch.directive('enableSwitch', [function () {
    return {
        restrict: 'E',
        templateUrl: 'templates/switch.html',
        controller: ['$scope', 'controlExtension', function ($scope, controlExtension) {
            chrome.storage.local.get(["enabled"], function (e) {
                let enabled = e.enabled
                //console.log("switch", enabled)
                $scope.onText = 'On';
                $scope.offText = 'Off';
                $scope.onColor = "primary";
                $scope.offColor = "default";
                $scope.size = 'mini';
                $scope.isSelected = enabled === true;
                var initialized = false;
                $scope.$watch('isSelected', function () {
                    if (!initialized) {
                        initialized = true;
                        return;
                    }
                    if ($scope.isSelected) {
                        controlExtension.enable();
                    } else {
                        controlExtension.disable();
                    }
                });
            });
        }]
    };
}]);