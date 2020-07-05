#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[4] = {"pulse_mode[off/continuous/single]", "pulse_amplitude[uA]",
        "time_between_pulses[ms]", "pulse_duration[us]"};
    validate_args(containers, argc, argv, "set_tes_pulse_params.exe", 4, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get full pulse parameters
    char* pulse_mode_real = argv[3];
    char* pulse_mode_dict[3] = {"off", "continuous", "single"};
    unsigned short pulse_mode = (unsigned short) get_index_str(pulse_mode_dict, 3, pulse_mode_real);

    double pulse_amplitude = stod(argv[4]);
    double time_between_pulses = stod(argv[5]);
    double pulse_duration = stod(argv[6]);

    double pulse_amplitude_coerced = 0;
    double time_between_pulses_coerced = 0;
    double pulse_duration_coerced = 0;

    MA_write_PulseParam(channel, &error, pulse_duration, time_between_pulses, pulse_mode,
        &pulse_duration_coerced, &time_between_pulses_coerced);
    errorout(error);

    MA_write_PhiX(channel, &error, pulse_amplitude, &pulse_amplitude_coerced);
    errorout(error);

    // Output
    printf("SUCCESS: Set TES pulse to %s mode with %f uA amplitude, %f us pulse duration, %f ms between pulses.\n",
        pulse_mode_real, pulse_amplitude_coerced, pulse_duration_coerced, time_between_pulses_coerced);
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
