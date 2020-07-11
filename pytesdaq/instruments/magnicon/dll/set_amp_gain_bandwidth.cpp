#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[2] = {"amp_gain[1100,1400,1700,2000; 220,280,340,400 if bw=Full]", "amp_bandwidth[0.2,0.7,1.4,Full,AC_Amp_off]"};
    validate_args(containers, argc, argv, "set_amp_gain_bandwidth.exe", 2, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get amplifier gain and bandwidth
    int amp_gain_real = stoi(argv[3]);
    unsigned short amp_gain = 0;
    string amp_bw_real = argv[4];
    unsigned short amp_bw = 0;

    if (amp_bw_real.compare("0.2") == 0) {
        amp_bw = 0; }
    else if (amp_bw_real.compare("0.7") == 0) {
        amp_bw = 1; }
    else if (amp_bw_real.compare("1.4") == 0) {
        amp_bw = 2; }
    else if (amp_bw_real.compare("Full") == 0) {
        amp_bw = 4; }
    else if (amp_bw_real.compare("AC_Amp_off") == 0) {
        amp_bw = 6; }
    else {
        cout << "ERROR: Invalid amplifier bandwidth." << endl;
        cout << flush;
        return 2;
    }

    if (amp_bw_real.compare("Full") == 0) {
        switch(amp_gain_real) {
            case 220:
                amp_gain = 0;
                break;
            case 280:
                amp_gain = 1;
                break;
            case 340:
                amp_gain = 2;
                break;
            case 400:
                amp_gain = 3;
                break;
            default:
                cout << "ERROR: Invalid amplifier gain." << endl;
                cout << flush;
                return 2;
        }
    }
    else {
        switch(amp_gain_real) {
            case 1100:
                amp_gain = 0;
                break;
            case 1400:
                amp_gain = 1;
                break;
            case 1700:
                amp_gain = 2;
                break;
            case 2000:
                amp_gain = 3;
                break;
            default:
                cout << "ERROR: Invalid amplifier gain." << endl;
                cout << flush;
                return 2;
        }
    }

    MA_write_AmpMode(channel, &error, amp_gain, amp_bw);
    errorout(error);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    // Output message so it can be read by SSH connection
    cout << "DONE" << endl;
    cout << flush;

    return 0;
}
