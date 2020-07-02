#include <iostream>
#include <string>
#include "magsv.h"
#include "squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    if (argc != 4 && argc != 6) {
        cout << "ERROR: run the program as follows" << endl;
        cout << "\t.\\get_dummy.exe channel[1,2,3] active[0,1] dummy_status[on/off] [baud = 57600] [timeout = 100]" << endl;
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
    string dummy = argv[3];

    // Connect to electronics
    MA_initUSB(&error, baud, timeout);
    errorout(error);

    // Set active channel if desired
    if (active == 1) {
        MA_SetActiveChannel(channel, &error);
        errorout(error);
    }

    // Get dummy
    if dummy.compare("off") == 0 {
        MA_write_Dummy(channel, &error, 0);
        errorout(error);
    }
    else if dummy.compare("on") == 0 {
        MA_write_Dummy(channel, &error, 1);
        errorout(error);
    }
    else
        cout << "ERROR: Invalid dummy status." << endl;
        cout << flush;
        return 2;
    }

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
