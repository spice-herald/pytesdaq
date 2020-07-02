#include <iostream>
#include <string>
#include "magsv.h"
#include "squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    if (argc != 5 && argc != 7) {
        cout << "ERROR: run the program as follows" << endl;
        cout << "\t.\\set_tes_current_bias.exe channel[1,2,3] active[0,1] range[low/high] bias_new [baud = 57600] [timeout = 100]" << endl;
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
    string iaux_range = argv[3];
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

    // Set current bias
    if (iaux_range.compare("low") == 0) {
        if (new_value < IAUX_LOW_MIN || new_value > IAUX_LOW_MAX) {
            cout << "ERROR: You attempted to set Iaux = " << new_value
                << ", but this is out of range. Not setting." << endl;
            cout << flush;
            return 2;
        }
        else {
            MA_write_Iaux(channel, &error, new_value, 0, &coerced_value);
            errorout(error);
        }
    }
    else if (iaux_range.compare("high") == 0) {
        if (new_value < IAUX_HIGH_MIN || new_value > IAUX_HIGH_MAX) {
            cout << "ERROR: You attempted to set Iaux = " << new_value
                << ", but this is out of range. Not setting." << endl;
            cout << flush;
            return 2;
        }
        else {
            MA_write_Iaux(channel, &error, new_value, 1, &coerced_value);
            errorout(error);
        }
    }
    else {
        cout << "ERROR: Invalid range." << endl;
        cout << flush;
        return 2;
    }

    cout << "SUCCESS: Set Iaux = " << coerced_value << endl;
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;
}
