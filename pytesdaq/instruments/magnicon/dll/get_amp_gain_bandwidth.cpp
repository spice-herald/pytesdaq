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
    validate_args(containers, argc, argv, "get_amp_gain_bandwidth.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get amplifier gain and bandwidth
    unsigned short amp_gain = 0;
    int amp_gain_real = 0;
    unsigned short amp_bw = 0;
    string amp_bw_real;

    MA_read_AmpMode(channel, &error, &amp_gain, &amp_bw);
    errorout(error);

    switch(amp_bw) {
        case 0:
            amp_bw_real = "0.2";
            break;
        case 1:
            amp_bw_real = "0.7";
            break;
        case 2:
            amp_bw_real = "1.4";
            break;
        case 4:
            amp_bw_real = "Full";
            break;
        case 6:
            amp_bw_real = "AC_Amp_off";
            break;
        default:
            cout << "ERROR getting amplifier bandwidth." << endl;
            cout << flush;
            return 2;
    }

    switch(amp_gain) {
        case 0:
            amp_gain_real = 1100;
            break;
        case 1:
            amp_gain_real = 1400;
            break;
        case 2:
            amp_gain_real = 1700;
            break;
        case 3:
            amp_gain_real = 2000;
            break;
        default:
            cout << "ERROR getting amplifier gain." << endl;
            cout << flush;
            return 2;
    }

    printf("SUCCESS: Read amp gain = %d, amp bandwidth = %s\n", amp_gain_real, amp_bw_real.c_str());
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
