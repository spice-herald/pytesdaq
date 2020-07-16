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
    validate_args(containers, argc, argv, "get_amp_or_fll.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get amp or fll mode
    unsigned short amp_or_fll = 0;
    MA_read_Amp(channel, &error, &amp_or_fll);
    errorout(error);
    if (amp_or_fll == 0) {
        cout << "SUCCESS: Electronics mode = 0 (AMP)" << endl;
    }
    else if (amp_or_fll == 1) {
        cout << "SUCCESS: Electronics mode = 1 (FLL)" << endl;
    }
    else {
        cout << "ERROR: Electronics mode not read correctly." << endl;
    }
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
