#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {"electronics_mode[AMP,FLL]"};
    validate_args(containers, argc, argv, "set_amp_or_fll.exe", 1, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get amp_or_fll
    string amp_or_fll = argv[3];
    if (amp_or_fll.compare("AMP") == 0) {
        MA_write_Amp(channel, &error, 0);
        errorout(error);
    }
    else if (amp_or_fll.compare("FLL") == 0) {
        MA_write_Amp(channel, &error, 1);
        errorout(error);
    }
    else {
        cout << "ERROR: Invalid electronics mode. Must be FLL or AMP." << endl;
        cout << flush;
        return 2;
    }

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
