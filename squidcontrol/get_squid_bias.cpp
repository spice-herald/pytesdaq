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
    if (argc != 4 && argc != 6) {
        cout << "ERROR: run the program as follows" << endl;
        cout << "\t.\\read_squid_bias.exe channel[1,2,3] active[0,1] bias_source[I,V,Phi] [baud = 57600] [timeout = 100]" << endl;
        cout << "\tNote: either set both baud and timeout or neither." << endl;
        cout << "\tNote: active indicates whether to make the channel the active channel." << endl;
        cout << flush;
        return 1;
    }

    // Set connection info
    unsigned short error = 0;
    unsigned long baud = 57600, timeout = 100; 
    if (argc == 6) {
        baud = stoul(argv[4]);
        timeout = stoul(argv[5]);
    }

    // Set user-defined arguments and other necessary containers
    unsigned short channel = (unsigned short)(stoul(argv[1]));
    unsigned short active = (unsigned short)(stoul(argv[2]));
    string source = argv[3];
    double bias = 0.;
    double ranges[3] = {0, 0, 0}; // array for Ib, Phib, and Vb range information
    long len = 3; // length of ranges[] array
    
    // Connect to electronics
    MA_initUSB(&error, baud, timeout);
    errorout(error);
    
    // Set active channel if desired
    if (active == 1) {
        MA_SetActiveChannel(channel, &error);
        errorout(error);
    }

    // Get relevant bias
    if (source.compare("I") == 0) {
        unsigned short Ib_range = 0; // meaningless, but a required argument
        MA_read_Ib(channel, &error, &ranges[0], len, &Ib_range, &bias);
        errorout(error);
    }
    else if (source.compare("V") == 0) {
        MA_read_Vb(channel, &error, &ranges[0], len, &bias);
        errorout(error);
    }
    else if (source.compare("Phi") == 0) {
        unsigned short PhibDisc = 0; // check if Phib is connected
        MA_read_PhibDisc(channel, &error, &PhibDisc);
        errorout(error);
        
        if (PhibDisc == 1) {
            MA_read_Phiob(channel, &error, &ranges[0], len, &bias);
            errorout(error);
        }
        else {
            cout << "ERROR: Flux bias is disconnected" << endl;
            return 2;
        }
    }
    else {
        cout << "ERROR: Invalid source to get." << endl;
        cout << flush;
        return 2;
    }

    cout << "SUCCESS: Get " << source << "b = " << bias << endl;
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;
}
