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
    validate_args(containers, argc, argv, "get_generator_onoff.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get generator and monitor status
    unsigned short gen1_onoff, gen2_onoff, mon_onoff;
    const char* onoff_dict[2] = {"off", "on"};
    MA_read_GenOnOff(channel, &error, &gen1_onoff, &gen2_onoff, &mon_onoff);
    errorout(error);

    // Output everything.
    printf("Generator 1 is %s. Generator 2 is %s. Monitoring is %s.\n",
        onoff_dict[gen1_onoff], onoff_dict[gen2_onoff], onoff_dict[mon_onoff]);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
