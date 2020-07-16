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
    validate_args(containers, argc, argv, "get_tes_pulse_params.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get full pulse parameters
    double time_ranges[3] = {0, 0, 0}; // arrays for pulse timing, duration, and amplitude
    double duration_ranges[3] = {0, 0, 0};
    double amplitude_ranges[3] = {0, 0, 0};
    long len = 3; // length of ranges[] arrays
    unsigned short pulse_mode = 0;
    const char* pulse_mode_dict[3] = {"off", "continuous", "single"};
    double time_between_pulses = 0;
    double pulse_duration = 0;
    double pulse_amplitude = 0;

    MA_read_PulseParam(channel, &error, &time_ranges[0], &duration_ranges[0], len,
        &pulse_mode, &time_between_pulses, &pulse_duration);
    errorout(error);

    MA_read_Phix(channel, &error, &amplitude_ranges[0], len, &pulse_amplitude);
    errorout(error);

    // Output
    printf("Pulse mode is %s, with an amplitude of %f uA, %f ms between pulses, a pulse duration of %f us.\n",
        pulse_mode_dict[pulse_mode], pulse_amplitude, time_between_pulses, pulse_duration);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
