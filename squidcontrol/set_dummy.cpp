#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {"dummy[on,off]"};
    validate_args(containers, argc, argv, "set_dummy.exe", 1, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get dummy
    string dummy = argv[3];
    if (dummy.compare("off") == 0) {
        MA_write_Dummy(channel, &error, 0);
        errorout(error);
    }
    else if (dummy.compare("on") == 0) {
        MA_write_Dummy(channel, &error, 1);
        errorout(error);
    }
    else {
        cout << "ERROR: Invalid dummy status. Must be on or off." << endl;
        cout << flush;
        return 2;
    }

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
