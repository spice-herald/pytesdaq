#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[2] = {"range[low/high]", "bias_new"};
    validate_args(containers, argc, argv, "set_tes_current_bias.exe", 2, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Containers
    string iaux_range = argv[3];
    double new_value = stod(argv[4]);
    double coerced_value = 0.;
    
    // Set current bias
    if (iaux_range.compare("low") == 0) {
        if (new_value < IAUX_LOW_MIN || new_value > IAUX_LOW_MAX) {
            cout << "ERROR: You attempted to set Iaux = " << new_value
                << ", but this is out of range. Not setting." << endl;
            cout << flush;
            return 2;
        }
        else {
            MA_write_Iaux(channel, &error, new_value, 0, &coerced_value);
            errorout(error);
        }
    }
    else if (iaux_range.compare("high") == 0) {
        if (new_value < IAUX_HIGH_MIN || new_value > IAUX_HIGH_MAX) {
            cout << "ERROR: You attempted to set Iaux = " << new_value
                << ", but this is out of range. Not setting." << endl;
            cout << flush;
            return 2;
        }
        else {
            MA_write_Iaux(channel, &error, new_value, 1, &coerced_value);
            errorout(error);
        }
    }
    else {
        cout << "ERROR: Invalid range. Must set be low or high." << endl;
        cout << flush;
        return 2;
    }

    cout << "SUCCESS: Set Iaux = " << coerced_value << endl;
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;
}
