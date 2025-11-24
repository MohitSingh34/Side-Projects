#include <iostream>
using namespace std;

int main(){
    int arr[5] = { 5,6,34,65,89 };
    cout << "1-D Array: " << endl;
    cout << arr[0] << " \t";
    cout << arr[1] << " \t";
    cout << arr[2] << " \t";
    cout << arr[3] << " \t";
    cout << arr[4] << endl;

    int arr2[2][3] = { 23,45,67,80,12,5 };
    cout << "2-D Array: " << endl;
    cout << arr2[0][0] << " \t";
    cout << arr2[0][1] << " \t";
    cout << arr2[0][2] << " \t";
    cout << arr2[1][0] << " \t";
    cout << arr2[1][1] << " \t";
    cout << arr2[1][2] << endl;
    return 0;
}