#include <iostream>
#include <time.h>
#include <thread>
#include <chrono>
#include <string>
#include "magsv.h"
#include "sc_functions.cpp"

using namespace std;

int main(int argc, char** argv) {
    
    if (argc == 1) {
        cout << "WIN\tWarning: The program will execute, but you have not set any parameters." << endl;
        cout << "\t\t\tRun like this: .\\squidcontrol_setup.exe [-dummy dummy(0/1)] [-mode mode(AMP/FLL)] [-Iaux range(low/high) Iaux] [-Vb Vb] [-Ib Ib] [-Phib Phib]" << endl;
    }

    unsigned short error = 0, channel = 2;
    unsigned long baud = 57600, timeout = 100; // default settings
    int status = 0;
    long t_start = time(NULL);
    
    // Connect to electronics
    cout << "WIN\tInitializing USB connection to electronics" << endl;
    MA_initUSB(&error, baud, timeout);
    errorout(error);
    
    // Set active channel, and read existing biases
    cout << "WIN\tReading current electronics settings" << endl;
    status = readStatus(channel, error);
    if (status != 0)
        return status;

    // Set user-defined params
    // Params, in order are: mode, Iaux_range, Iaux, Vb, Ib, Phib, time to run, dummy mode
    cout << endl << "WIN\tSetting initial parameters" << endl;
    double params[8] = {1e9, 1e9, 1e9, 1e9, 1e9, 1e9, 1e9, 1e9};
    loadConfig(argc, argv, params);

    if (params[7] < 9e8) {
        setDummy(channel, error, (unsigned short)(params[7]));
    }    
    if (params[0] < 9e8) {
        setAmpMode(channel, error, params[0]);
    }
    if (params[1] < 9e8 && params[2] < 9e8) {
        setIaux(channel, error, params[2], params[1]);
    }
    if (params[3] < 9e8) {
        setVb(channel, error, params[3]);
    }
    if (params[4] < 9e8) {
        setIb(channel, error, params[4]);
    }
    if (params[5] < 9e8) {
        setPhib(channel, error, params[5]);
    }

    // Read amplification gain
    unsigned short amp_gain = 0, amp_bw = 0;
    int amp_gain_dict[4] = {1100, 1400, 1700, 2000};
    double amp_bw_dict[7] = {0.2, 0.7, 1.4, 0, 100, 0, 0};
    MA_read_AmpMode(channel, &error, &amp_gain, &amp_bw);

    // Close electronics connection
    cout << endl;
    cout << "WIN\tClosing connection to electronics" << endl;
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;    
}
