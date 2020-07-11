#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[3] = {"generator_1_status[on,off]", "generator_2_status[on,off]", "monitor_status[on,off]"};
    validate_args(containers, argc, argv, "set_gen_onoff.exe", 3, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Set gen_onoff for both generators and monitoring output
    char* gen1_onoff_real = argv[3];
    char* gen2_onoff_real = argv[4];
    char* mon_onoff_real = argv[5];

    char* onoff_dict[2] = {"off", "on"};
    unsigned short gen1_onoff= (unsigned short) get_index_str(onoff_dict, 2, gen1_onoff_real);
    unsigned short gen2_onoff= (unsigned short) get_index_str(onoff_dict, 2, gen2_onoff_real);
    unsigned short mon_onoff= (unsigned short) get_index_str(onoff_dict, 2, mon_onoff_real);

    MA_write_GenOnOff(channel, &error, gen1_onoff, gen2_onoff, mon_onoff);
    errorout(error);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    // Output message so it can be read by SSH connection
    cout << "DONE" << endl;
    cout << flush;

    return 0;
}
