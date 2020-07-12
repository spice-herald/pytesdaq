#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    cout << "Warning: This function is only useful for turning on single shot pulse mode." << endl;
    cout << "To turn on or off the continuous pulse mode, or to turn off single shot, use set_tes_pulse_params.cpp" << endl;

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {"tes_pulse_status[on,off]"};
    validate_args(containers, argc, argv, "set_tes_pulse_onoff.exe", 1, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Set tes_pulse_onoff for both generators and monitoring output
    char* tes_pulse_onoff_real = argv[3];

    char* onoff_dict[2] = {"off", "on"};
    unsigned short tes_pulse_onoff = (unsigned short) get_index_str(onoff_dict, 2, tes_pulse_onoff_real);

    MA_write_PulseOnOff(channel, &error, tes_pulse_onoff);
    errorout(error);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    // Output message so it can be read by SSH connection
    cout << "DONE" << endl;
    cout << flush;

    return 0;
}
