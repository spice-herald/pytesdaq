#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {"squid_gain_sign[negative,positive]"};
    validate_args(containers, argc, argv, "set_squid_gain_sign.exe", 1, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get squid gain sign
    string squid_gain_sign = argv[3];
    if (squid_gain_sign.compare("positive") == 0) {
        MA_write_SGain(channel, &error, 0);
        errorout(error);
    }
    else if (squid_gain_sign.compare("negative") == 0) {
        MA_write_SGain(channel, &error, 1);
        errorout(error);
    }
    else {
        cout << "ERROR: Invalid squid gain sign. Must be positive or negative." << endl;
        cout << flush;
        return 2;
    }

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    // Output message so it can be read by SSH connection
    cout << "DONE" << endl;
    cout << flush;

    return 0;
}
