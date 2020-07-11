#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {"Rf[off,0.70,0.75,0.91,1.00,2.14,2.31,2.73,3.00,7.00,7.50,9.10,10.00,23.10,30.00,100.00]"};
    validate_args(containers, argc, argv, "set_feedback_resistor.exe", 1, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get AMP/FLL mode
    unsigned short amp_or_fll = 0;
    MA_read_Amp(channel, &error, &amp_or_fll);
    errorout(error);

    // Convert feedback resistor
    char* Rf_dict[16] = {"off", "0.07", "0.75", "0.91", "1.00", "2.14", "2.31",
        "2.73", "3.00", "7.00", "7.50", "9.10", "10.00", "23.10", "30.00", "100.00"};
    char* Rf_real = argv[3];
    unsigned short Rf = (unsigned short) get_index_str(Rf_dict, 16, Rf_real);

    // Set feedback resistor
    if (amp_or_fll == 0) {
        MA_write_RfAmp(channel, &error, Rf);
        errorout(error);
    }
    else if (amp_or_fll == 1) {
        MA_write_RfFLL(channel, &error, Rf);
        errorout(error);
    }

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    // Output message so it can be read by SSH connection
    cout << "DONE" << endl;
    cout << flush;

    return 0;
}
