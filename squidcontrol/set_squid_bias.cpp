#include <iostream>
#include <time.h>
#include <thread>
#include <chrono>
#include <string>
#include "magsv.h"
#include "sc_functions.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    if (argc != 5 && argc != 7) {
        cout << "ERROR: run the program as follows" << endl;
        cout << "\t.\\read_squid_bias.exe channel[1,2,3] active[0,1] bias_source[I,V,Phi] bias_new [baud = 57600] [timeout = 100]" << endl;
        cout << "\tNote: either set both baud and timeout or neither." << endl;
        cout << "\tNote: active indicates whether to make the channel the active channel." << endl;
        cout << flush;
        return 1;
    }

    // Set connection info
    unsigned short error = 0;
    unsigned long baud = 57600, timeout = 100; 
    if (argc == 7) {
        baud = stoul(argv[5]);
        timeout = stoul(argv[6]);
    }

    // Set user-defined arguments
    unsigned short channel = (unsigned short)(stoul(argv[1]));
    unsigned short active = (unsigned short)(stoul(argv[2]));
    string source = argv[3];
    double new_value = stod(argv[4]);
    double coerced_value = 0.;
    
    // Connect to electronics
    MA_initUSB(&error, baud, timeout);
    errorout(error);
    
    // Set active channel if desired
    if (active == 1) {
        MA_SetActiveChannel(channel, &error);
        errorout(error);
    }

    // Set relevant bias
    if (source.compare("I") == 0) {
        if (new_value < IB_MIN || new_value > IB_MAX) {
            cout << "ERROR: You attempted to set Ib = " << new_value
                << ", but this is out of range. Not setting." << endl;
            cout << flush;
            return 2;
        }
        else {
            MA_write_Ib(channel, &error, new_value, 0, &coerced_value);
            errorout(error);
        }
    }
    else if (source.compare("V") == 0) {
        if (new_value < VB_MIN || new_value > VB_MAX) {
            cout << "ERROR: You attempted to set Vb = " << new_value
                << ", but this is out of range. Not setting." << endl;
            cout << flush;
            return 2;
        }
        else {
            MA_write_Vb(channel, &error, new_value, &coerced_value);
            errorout(error);
        }
    }
    else if (source.compare("Phi") == 0) {
        unsigned short PhibDisc = 0; // check if Phib is connected
        MA_read_PhibDisc(channel, &error, &PhibDisc);
        errorout(error);
        
        if (PhibDisc == 0) {
            cout << "ERROR: Flux bias is disconnected." << endl;
            cout << flush;
            return 2;
        }
        else if (new_value < PHIB_MIN || new_value > PHIB_MAX) {
            cout << "ERROR: You attempted to set Phib = " << new_value
                << ", but this is out of range. Not setting." << endl;
            cout << flush;
            return 2;
        }
        else {
            MA_write_Phiob(channel, &error, new_value, &coerced_value);
            errorout(error);
        }
    }
    else {
        cout << "ERROR: Invalid source to set." << endl;
        cout << flush;
        return 2;
    }

    cout << "SUCCESS: Set " << source << "b = " << coerced_value << endl;
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;
}
