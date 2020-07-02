#include <iostream>
#include <time.h>
#include <thread>
#include <chrono>
#include <string>
#include "magsv.h"
#include "sc_functions.cpp"

using namespace std;

int main(int argc, char** argv) {

    if (argc != 3 && argc != 5) {
        cout << "WIN\tError: run the program as follows (you either set both baud and timeout or neither)" << endl;
        cout << "\t\t\t.\\sc_setIb.exe channel_no Ib_new [baud = 57600] [timeout = 100]" << endl;
        return 1;
    }

    unsigned short error = 0;
    unsigned long baud = 57600, timeout = 100; 
    if (argc == 5) {
        baud = stoul(argv[3]);
        timeout = stoul(argv[4);
    }
    
    // Connect to electronics
    MA_initUSB(&error, baud, timeout);
    errorout(error);
    
    setIb(stoi(argv[1]), error, stod(argv[2]));
    
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;    
}
