#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[2] = {"bias_source[I,V,Phi]", "bias_new"};
    validate_args(containers, argc, argv, "set_squid_bias.exe", 2, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Containers
    string source = argv[3];
    double new_value = stod(argv[4]);
    double coerced_value = 0.;
    
    // Set relevant bias
    if (source.compare("I") == 0) {
        if (new_value < IB_MIN || new_value > IB_MAX) {
            cout << "ERROR: You attempted to set Ib = " << new_value
                << ", but this is out of range. Not setting." << endl;
            cout << flush;
            return 2;
        }
        else {
            MA_write_Ib(channel, &error, new_value, 0, &coerced_value);
            errorout(error);
        }
    }
    else if (source.compare("V") == 0) {
        if (new_value < VB_MIN || new_value > VB_MAX) {
            cout << "ERROR: You attempted to set Vb = " << new_value
                << ", but this is out of range. Not setting." << endl;
            cout << flush;
            return 2;
        }
        else {
            MA_write_Vb(channel, &error, new_value, &coerced_value);
            errorout(error);
        }
    }
    else if (source.compare("Phi") == 0) {
        unsigned short PhibDisc = 0; // check if Phib is connected
        MA_read_PhibDisc(channel, &error, &PhibDisc);
        errorout(error);
        
        if (PhibDisc == 0) {
            cout << "ERROR: Flux bias is disconnected." << endl;
            cout << flush;
            return 2;
        }
        else if (new_value < PHIB_MIN || new_value > PHIB_MAX) {
            cout << "ERROR: You attempted to set Phib = " << new_value
                << ", but this is out of range. Not setting." << endl;
            cout << flush;
            return 2;
        }
        else {
            MA_write_Phiob(channel, &error, new_value, &coerced_value);
            errorout(error);
        }
    }
    else {
        cout << "ERROR: Invalid source to set. Must be I, V, or Phi." << endl;
        cout << flush;
        return 2;
    }

    cout << "SUCCESS: Set " << source << "b = " << coerced_value << endl;
    cout << flush;

    // Close connection
    MA_closeUSB(&error);
    errorout(error);
    
    return 0;
}
