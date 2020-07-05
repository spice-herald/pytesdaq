#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[8] = {"generator_number[1,2]", "frequency[Hz]",
        "source[Ib,Vb,Phib,I]",
        "waveform[triangle,sawtoothpos,sawtoothneg,square,sine,noise]",
        "phase_shift[0,90,180,270]",
        "freq_div[off,2,4,8,16,32,64,128,256,512,1024]",
        "half_peak_peak_offset[on,off]", "peak_peak_amplitude"};
    validate_args(containers, argc, argv, "set_generator_params.exe", 8, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Convert generator number
    unsigned short gen_num = stoi(argv[3]);
    if (gen_num != 1 && gen_num != 2) {
        cout << "ERROR: Invalid generator number. Must be 1 or 2." << endl;
        cout << flush;
        return 2;
    }

    // Set generator frequency
    double gen_freq = stod(argv[4]);
    double gen_freq_coerced = 0;
    MA_write_GenFreq(channel, &error, gen_freq, &gen_freq_coerced);
    errorout(error);

    // Set waveform information
    char* source_dict[7] = {"Ib", "Vb", "", "Phib", "I", "", "PhiX"};
    char* waveform_dict[6] = {"triangle", "sawtoothpos",
        "sawtoothneg", "square", "sine", "noise"};
    int phase_shift_dict[4] = {0, 90, 180, 270};
    char* freq_div_dict[11] = {"off", "2", "4", "8", "16", "32",
        "64", "128", "256", "512", "1024"};
    char* half_pp_offset_dict[2] = {"off", "on"};

    char* source_real = argv[5];
    char* waveform_real = argv[6];
    int phase_shift_real = stoi(argv[7]);
    char* freq_div_real = argv[8];
    char* half_pp_offset_real = argv[9];
    double pp_amplitude = stod(argv[10]);
    double pp_amplitude_coerced = 0.;

    unsigned short source = (unsigned short) get_index_str(source_dict, 7, source_real);
    unsigned short waveform = (unsigned short) get_index_str(waveform_dict, 6, waveform_real);
    unsigned short phase_shift = (unsigned short) get_index_int(phase_shift_dict, 4, phase_shift_real);
    unsigned short freq_div = (unsigned short) get_index_str(freq_div_dict, 11, freq_div_real);
    unsigned short half_pp_offset = (unsigned short) get_index_str(half_pp_offset_dict, 2, half_pp_offset_real);

    MA_write_GenParam(channel, &error, gen_num, waveform, source, pp_amplitude,
        phase_shift, freq_div, half_pp_offset, &pp_amplitude_coerced);
    errorout(error);

    printf("SUCCESS: Set generator %d to peak-peak amplitude of %f and frequency of %f Hz.\n",
        gen_num, pp_amplitude_coerced, gen_freq_coerced);
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
