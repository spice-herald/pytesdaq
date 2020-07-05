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
    validate_args(containers, argc, argv, "get_dummy.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get dummy
    unsigned short dummy = 0;
    MA_read_Dummy(channel, &error, &dummy);
    errorout(error);
    if (dummy == 0) {
        cout << "SUCCESS: Dummy = 0 (off)" << endl;
    }
    else if (dummy == 1) {
        cout << "SUCCESS: Dummy = 1 (on)" << endl;
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
