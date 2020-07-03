#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {"electronics_coupling[DC,AC]"};
    validate_args(containers, argc, argv, "set_output_coupling.exe", 1, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get output_coupling
    string output_coupling = argv[3];
    if (output_coupling.compare("DC") == 0) {
        MA_write_OutCoup(channel, &error, 0);
        errorout(error);
    }
    else if (output_coupling.compare("AC") == 0) {
        MA_write_OutCoup(channel, &error, 1);
        errorout(error);
    }
    else {
        cout << "ERROR: Invalid electronics mode. Must be DC or AC." << endl;
        cout << flush;
        return 2;
    }

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
