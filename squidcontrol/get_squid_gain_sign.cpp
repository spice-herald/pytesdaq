#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {};
    validate_args(containers, argc, argv, "get_squid_gain_sign.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get amp gain sign
    unsigned short squid_gain_sign = 0;
    MA_read_SGain(channel, &error, &squid_gain_sign);
    errorout(error);
    if (squid_gain_sign == 0) {
        cout << "SUCCESS: Squid Gain Sign = 0 (positive)" << endl;
    }
    else if (squid_gain_sign == 1) {
        cout << "SUCCESS: Squid Gain Sign = 1 (negative)" << endl;
    }
    else {
        cout << "ERROR: Squid gain not read correctly." << endl;
    }
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
