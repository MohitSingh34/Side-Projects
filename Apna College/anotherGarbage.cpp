#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

int main()
{
    int age;

    // Some compilers in debug mode fill with specific patterns:
    // 0xCCCCCCCC (MSVC debug) → -858993460
    // 0xCDCDCDCD (MSVC clean memory)
    // 0xFEFEFEFE (Memory guard)

    cout << age; // Might see these special values in debug mode

    return 0;
}