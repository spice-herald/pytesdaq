#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {"generator_number[1,2]"};
    validate_args(containers, argc, argv, "get_generator.exe", 1, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get generator number
    unsigned short gen_num = stoi(argv[3]);
    if (gen_num != 1 && gen_num != 2) {
        cout << "ERROR: Invalid generator number. Must be 1 or 2." << endl;
        cout << flush;
        return 2;
    }

    // Get generator frequency
    double gen_freq = 0.;
    double ranges_freq[3] = {0, 0, 0}; // array for frequency range
    long len = 3; // length of ranges[] array
    MA_read_GenFreq(channel, &error, &ranges_freq[0], len, &gen_freq);
    errorout(error);

    // Get waveform information
    double ranges_source[3] = {0, 0, 0}; // array for source range
    unsigned short waveform, phase_shift, freq_div, half_pp_offset, source;
    double pp_amplitude; // peak-to-peak amplitude
    MA_read_GenParam(channel, &error, gen_num, &ranges_source[0], len,
        &waveform, &phase_shift, &freq_div, &half_pp_offset, &source,
        &pp_amplitude);
    errorout(error);

    const char* waveform_dict[6] = {"triangle", "sawtoothpos",
        "sawtoothneg", "square", "sine", "noise"};
    const int phase_shift_dict[4] = {0, 90, 180, 270};
    const char* freq_div_dict[11] = {"off", "2", "4", "8", "16", "32",
        "64", "128", "256", "512", "1024"};
    const char* half_pp_offset_dict[2] = {"off", "on"};
    const char* source_dict[7] = {"Ib", "Vb", "Test2", "Phib", "I", "Test5", "PhiX"};

    // Output everything.
    printf("Generator %d: ", gen_num);
    printf("The source is %s. The waveform is %s with a frequency of %f Hz, the divider at %s and a phase shift of %d. ",
        source_dict[source], waveform_dict[waveform], gen_freq, freq_div_dict[freq_div], phase_shift_dict[phase_shift]);
    printf("The peak-to-peak amplitude is %f, with the half-peak-to-peak offset %s.\n",
        pp_amplitude, half_pp_offset_dict[half_pp_offset]);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
