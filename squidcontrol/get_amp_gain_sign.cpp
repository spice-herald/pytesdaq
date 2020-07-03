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
    validate_args(containers, argc, argv, "get_amp_gain_sign.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get amp gain sign
    unsigned short amp_gain_sign = 0;
    MA_read_AGain(channel, &error, &amp_gain_sign);
    errorout(error);
    if (amp_gain_sign == 0) {
        cout << "SUCCESS: Amp Gain Sign = 0 (negative)" << endl;
    }
    else if (amp_gain_sign == 1) {
        cout << "SUCCESS: Amp Gain Sign = 1 (positive)" << endl;
    }
    else {
        cout << "ERROR: Dummy not read correctly." << endl;
    }
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
