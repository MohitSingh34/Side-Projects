#include <iostream>
using namespace std;

void demonstrateGarbageValues()
{
    // Example 1: Simple uninitialized variable
    int age;
    cout << "Uninitialized age: " << age << endl;

    // Example 2: Multiple variables showing different values
    int a, b, c;
    cout << "Garbage values: " << a << ", " << b << ", " << c << endl;

    // Example 3: Array with garbage values
    int arr[5];
    cout << "Array garbage: ";
    for (int i = 0; i < 5; i++)
    {
        cout << arr[i] << " ";
    }
    cout << endl;
}

void showMemoryReuse()
{
    // First, use some memory
    int x = 100;
    int y = 200;
    cout << "Initial values: x=" << x << ", y=" << y << endl;

    // Now declare new variables - might reuse same memory
    int a, b;
    cout << "New vars in same area: a=" << a << ", b=" << b << endl;
}

int main()
{
    cout << "=== Demonstration of Uninitialized Variables ===" << endl;

    demonstrateGarbageValues();
    cout << endl
         << "--- Memory Reuse Example ---" << endl;
    showMemoryReuse();

    return 0;
}