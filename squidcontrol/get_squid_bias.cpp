#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {"bias_source[I,V,Phi]"};
    validate_args(containers, argc, argv, "get_squid_bias.exe", 1, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Containers
    string source = argv[3];
    double bias = 0.;
    double ranges[3] = {0, 0, 0}; // array for Ib, Phib, and Vb range information
    long len = 3; // length of ranges[] array
    
    // Get relevant bias
    if (source.compare("I") == 0) {
        unsigned short Ib_range = 0; // meaningless, but a required argument
        MA_read_Ib(channel, &error, &ranges[0], len, &Ib_range, &bias);
        errorout(error);
    }
    else if (source.compare("V") == 0) {
        MA_read_Vb(channel, &error, &ranges[0], len, &bias);
        errorout(error);
    }
    else if (source.compare("Phi") == 0) {
        unsigned short PhibDisc = 0; // check if Phib is connected
        MA_read_PhibDisc(channel, &error, &PhibDisc);
        errorout(error);
        
        if (PhibDisc == 1) {
            MA_read_Phiob(channel, &error, &ranges[0], len, &bias);
            errorout(error);
        }
        else {
            cout << "ERROR: Flux bias is disconnected" << endl;
            return 2;
        }
    }
    else {
        cout << "ERROR: Invalid source to get." << endl;
        cout << flush;
        return 2;
    }

    cout << "SUCCESS: Get " << source << "b = " << bias << endl;
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;
}
