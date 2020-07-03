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
    validate_args(containers, argc, argv, "get_tes_current_bias.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Containers
    unsigned short iaux_range = 0;
    double bias = 0.;
    double ranges[3] = {0, 0, 0}; // array for Iaux range information
    long len = 3; // length of ranges[] array
    
    // Get current bias
    MA_read_Iaux(channel, &error, &ranges[0], len, &iaux_range, &bias);
    errorout(error);

    if (iaux_range == 0) {
        cout << "SUCCESS: Get Iaux = " << bias << " (low mode)" << endl;
    }
    else if (iaux_range == 1) {
        cout << "SUCCESS: Get Iaux = " << bias << " (high mode)" << endl;
    }
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;
}
