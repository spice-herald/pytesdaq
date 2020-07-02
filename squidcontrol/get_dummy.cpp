#include <iostream>
#include <string>
#include "magsv.h"
#include "squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    if (argc != 3 && argc != 5) {
        cout << "ERROR: run the program as follows" << endl;
        cout << "\t.\\get_dummy.exe channel[1,2,3] active[0,1] [baud = 57600] [timeout = 100]" << endl;
        cout << "\tNote: either set both baud and timeout or neither." << endl;
        cout << "\tNote: active indicates whether to make the channel the active channel." << endl;
        cout << flush;
        return 1;
    }

    // Set connection info
    unsigned short error = 0;
    unsigned long baud = 57600, timeout = 100; 
    if (argc == 5) {
        baud = stoul(argv[3]);
        timeout = stoul(argv[4]);
    }

    // Set user-defined arguments and other necessary containers
    unsigned short channel = (unsigned short)(stoul(argv[1]));
    unsigned short active = (unsigned short)(stoul(argv[2]));
    unsigned short dummy = 0;

    // Connect to electronics
    MA_initUSB(&error, baud, timeout);
    errorout(error);

    // Set active channel if desired
    if (active == 1) {
        MA_SetActiveChannel(channel, &error);
        errorout(error);
    }

    // Get dummy
    MA_read_Dummy(channel, &error, &dummy);
    errorout(error);
    if (dummy == 0) {
        cout << "SUCCESS: Dummy = 0 (off)" << endl;
    }
    else {
        cout << "SUCCESS: Dummy = 1 (on)" << endl;
    }
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
