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
    validate_args(containers, argc, argv, "get_feedback_resistor.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get AMP/FLL mode
    unsigned short amp_or_fll = 0;
    char* amp_or_fll_dict[2] = {"AMP", "FLL"};
    MA_read_Amp(channel, &error, &amp_or_fll);
    errorout(error);

    // Get feedback resistor
    unsigned short Rf = 0;
    if (amp_or_fll == 0) {
        MA_read_RfAmp(channel, &error, &Rf);
        errorout(error);
    }
    else if (amp_or_fll == 1) {
        MA_read_RfFLL(channel, &error, &Rf);
        errorout(error);
    }

    // Print results
    char* Rf_dict[16] = {"off", "0.7", "0.75", "0.91", "1.0", "2.14", "2.31",
        "2.73", "3.0", "7.0", "7.5", "9.1", "10.0", "23.1", "30", "100"};
    printf("SUCCESS: Rf = %s (%s)\n", Rf_dict[Rf], amp_or_fll_dict[amp_or_fll]);
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
