#include <iostream>
using namespace std;

int main() {
    int arr[] = {60, 7, 8, 3, 20};
    cout << "Given Array: ";
    int n = sizeof(arr)/sizeof(arr[0]);
    
    for(int i=0; i<n; i++){
        cout << arr[i] << "\t";
    }
    cout << endl;
    
    for(int i=0; i<n-1; i++){
        for(int j=0; j<n-i-1; j++){
            if(arr[j]>arr[j+1]) {
                int swap = arr[j];
                arr[j] = arr[j+1];
                arr[j+1] = swap;
            }
        }
    }
    
    cout << "Sorted Array: ";
    for(int i=0; i<n; i++){
        cout << arr[i] << "\t";
    }
    return 0;
}