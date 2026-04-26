import base64

cpp = r'''#include<iostream>
using namespace std;
void fn(){cout<<"hmm function?"<<endl;for(int i=0;i<6;i++){cout<<"std::pln('Hello, World!')"<<endl;}}
int main(){int x=5;cout<<"std!!"<<endl;if(x!=5){cout<<"oh not 5?"<<endl;}else if(x==5){cout<<"yes 5!"<<endl;}else{cout<<"idk bruh"<<endl;}fn();return 0;}'''

# binary (for visualization)
binary = ''.join(format(b, '08b') for b in cpp.encode())

# hex encoding
hexed = binary.encode().hex()

# base64 encoding (final answer)
b64 = base64.b64encode(hexed.encode()).decode()

print("BINARY:", binary)
print("HEX:", hexed)
print("BASE64:", b64)