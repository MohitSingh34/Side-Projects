control = angular.module("controlPage", [
    'translateFilter',
    'reviewBox',
    'enableDisableSwitch',
    'ultrasurfNavbar',
    'statusMonitor',
    'stateMonitor'
]).config([
    '$compileProvider',
    function ($compileProvider) {
        $compileProvider.aHrefSanitizationWhitelist(/^\s*(chrome-extension):/);
        $compileProvider.imgSrcSanitizationWhitelist(/^\s*(chrome-extension):/);
    }
]);

control.controller('ControlPageCtrl', ['$scope', 'ratingStore', function ($scope, ratingStore) {
    $scope.ratingStore = ratingStore;
}]);
