#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {};
    validate_args(containers, argc, argv, "get_output_coupling.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get ac or dc coupling
    unsigned short output_coupling = 0;
    MA_read_OutCoup(channel, &error, &output_coupling);
    errorout(error);
    if (output_coupling == 0) {
        cout << "SUCCESS: Electronics coupling = 0 (DC)" << endl;
    }
    else if (output_coupling == 1) {
        cout << "SUCCESS: Electronics coupling = 1 (AC)" << endl;
    }
    else {
        cout << "ERROR: Electronics coupling not read correctly." << endl;
    }
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
