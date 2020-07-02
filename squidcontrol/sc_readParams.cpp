#include <iostream>
#include <time.h>
#include <thread>
#include <chrono>
#include <string>
#include "magsv.h"
#include "sc_functions.cpp"

using namespace std;

int main(int argc, char** argv) {
    
    if (argc != 1) {
        cout << "WIN\tWarning: The program will execute, but your input parameters are not being considered." << endl;
    }

    unsigned short error = 0, channel = 3;
    unsigned long baud = 57600, timeout = 100; // default settings
    int status = 0;
    long t_start = time(NULL);
    
    // Connect to electronics
    cout << "WIN\tInitializing USB connection to electronics" << endl;
    MA_initUSB(&error, baud, timeout);
    errorout(error);
    
    // Set active channel, and read existing biases
    cout << "WIN\tReading current electronics settings" << endl;
    status = readStatus(channel, error);
    if (status != 0)
        return status;

    // Close electronics connection
    cout << endl;
    cout << "WIN\tClosing connection to electronics" << endl;
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;    
}
