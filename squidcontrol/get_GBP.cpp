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
    validate_args(containers, argc, argv, "get_GBP.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get gain bandwidth product
    unsigned short gbp = 0;
    MA_read_GBP(channel, &error, &gbp);
    errorout(error);

    double gbp_dict[19] = {0.23, 0.27, 0.30, 0.38, 0.47, 0.55, 0.66, 0.82,
        1.04, 1.28, 1.50, 1.80, 2.25, 2.80, 3.30, 4.00, 5.00, 6.20, 7.20};
    printf("SUCCESS: Gain bandwidth product = %.2f GHz\n", gbp_dict[gbp]);
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
