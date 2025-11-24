#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

class first
{
public:
    int number;
    string name;
    void print();
};

void first::print()
{
    cout << "Number: " << number << ", Name: " << name << endl;
}

int main()
{
    first obj;
    obj.number = 1;
    obj.name = "Example";
    obj.print();
    return 0;
}