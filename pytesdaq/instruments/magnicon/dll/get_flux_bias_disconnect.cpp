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
    validate_args(containers, argc, argv, "get_flux_bias_disconnect.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get status of flux bias switch
    unsigned short flux_bias_disconnect;
    const char* disconnect_dict[2] = {"disconnected", "connected"};
    MA_read_PhibDisc(channel, &error, &flux_bias_disconnect);
    errorout(error);

    // Output
    printf("Flux bias switch is %s\n", disconnect_dict[flux_bias_disconnect]);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
