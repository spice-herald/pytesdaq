#include <iostream>
#include <time.h>
#include <thread>
#include <chrono>
#include <string>
#include "magsv.h"
#include "sc_functions.cpp"

using namespace std;

int main(int argc, char** argv) {
    
    if (argc != 2) {
        cout << "WIN\tError: run the program as follows" << endl;
        cout << "\t\t\t.\\sc_setPhib.exe Phib_new" << endl;
        return 1;
    }

    unsigned short error = 0, channel = 1;
    unsigned long baud = 57600, timeout = 100; 
    
    // Connect to electronics
    MA_initUSB(&error, baud, timeout);
    errorout(error);
    
    setPhib(channel, error, stod(argv[1]));
    
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;    
}
