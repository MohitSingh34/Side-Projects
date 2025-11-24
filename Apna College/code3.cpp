#include <iostream>
using namespace std;

int main(){
    int arr1[3][3] = {22, 46, 67, 87, 34, 9, 62, 88, 90};
    int arr2[3][3] = {67, 34, 43, 22, 76, 203, 221, 517, 515};
    int res[3][3] = {};
    
    for(int i=0; i<3; i++) {
        for(int j=0; j<3; j++) {
            res[i][j] = arr1[i][j] + arr2[i][j];
        }
    }
    
    cout << "First array is:" << endl;
    for(int i=0; i<3; i++) {
        for(int j=0; j<3; j++) {
            cout << arr1[i][j] << "\t";
        }
        cout << endl;
    }
    
    cout << "Second array is:" << endl;
    for(int i=0; i<3; i++) {
        for(int j=0; j<3; j++) {
            cout << arr2[i][j] << "\t";
        }
        cout << endl;
    }
    
    cout << "Merged array is:" << endl;
    for(int i=0; i<3; i++) {
        for(int j=0; j<3; j++) {
            cout << res[i][j] << "\t";
        }
        cout << endl;
    }
    return 0;
}