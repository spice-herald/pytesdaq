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
    validate_args(containers, argc, argv, "get_tes_pulse_disconnect.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get disconnect switch status for auxiliary current source
    unsigned short tes_pulse_disconnect;
    const char* disconnect_dict[2] = {"disconnected", "connected"};
    MA_read_PhixDisc(channel, &error, &tes_pulse_disconnect);
    errorout(error);

    // Output
    printf("TES current pulse switch is %s\n", disconnect_dict[tes_pulse_disconnect]);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
