#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"

using namespace std;

const double IB_MIN = 0., IB_MAX = 180.;
const double VB_MIN = 0., VB_MAX = 1300.;
const double PHIB_MIN = -125., PHIB_MAX = 125.;
const double IAUX_LOW_MIN = -125., IAUX_LOW_MAX = 125.;
const double IAUX_HIGH_MIN = -500., IAUX_HIGH_MAX = 500.;



void errorout(unsigned short error) {
    if (error != 0)
        cout << "\nCommunication Error" << endl;
}



// Check user's command-line arguments for general validity
// Check the number of arguments given, and if appropriate, open USB connection and set the active channel.
// Arguments: argc and argv from the command-line arguments; the number of extra arguments in addition to
// the call, channel, whether to set active, baud, and timeout (i.e. argc minus 5); the function call
// in the form *.exe
// Returns: an unsigned short array with three elements: channel, active, and error

unsigned short* validate_args(int argc, char** argv, int extra_args, string exe_name) {

    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};

    // Check number of arguments
    if (argc != (3 + extra_args) && argc != (5 + extra_args)) {
        cout << "ERROR: run the program as follows" << endl;
        printf("\t.\\%s channel[1,2,3] active[0,1] [baud = 57600] [timeout = 100]\n", exe_name);
        cout << "\tNote: either set both baud and timeout or neither." << endl;
        cout << "\tNote: active indicates whether to make the channel the active channel." << endl;
        cout << flush;
        return containers;
    }

    // Set connection info
    unsigned long baud = 57600, timeout = 100; 
    if (argc == (5 + extra_args)) {
        baud = stoul(argv[3 + extra_args]);
        timeout = stoul(argv[4 + extra_args]);
    }

    // Set containers: channel, whether to set active, error
    unsigned short channel = (unsigned short)(stoul(argv[1]));
    unsigned short active = (unsigned short)(stoul(argv[2]));
    unsigned short error = 0;

    // Connect to electronics
    MA_initUSB(&error, baud, timeout);
    errorout(error);

    // Set active channel if desired
    if (active == 1) {
        MA_SetActiveChannel(channel, &error);
        errorout(error);
    }

    // Return containers
    containers[0] = channel;
    containers[1] = active;
    containers[2] = error;
    return containers;
}
