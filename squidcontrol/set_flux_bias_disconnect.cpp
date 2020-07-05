#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {"flux_bias_switch[disconnected,connected]"};
    validate_args(containers, argc, argv, "set_flux_bias_disconnect.exe", 1, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Set disconnect switch for flux bias
    string flux_bias_disconnect_real = argv[3];

    char* disconnect_dict[2] = {"disconnected", "connected"};
    unsigned short flux_bias_disconnect = (unsigned short) get_index_str(disconnect_dict, 2, flux_bias_disconnect_real);

    MA_write_PhibDisc(channel, &error, flux_bias_disconnect);
    errorout(error);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
