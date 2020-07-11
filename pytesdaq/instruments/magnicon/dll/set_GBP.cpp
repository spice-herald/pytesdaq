#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "utils/squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {"GBP[0.23,0.27,0.30,0.38,0.47,0.55,0.66,0.82,1.04,1.28,1.50,1.80,2.25,2.80,3.30,4.00,5.00,6.20,7.20]"};
    validate_args(containers, argc, argv, "set_GBP.exe", 1, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Convert gain bandwidth product
    char* gbp_dict[19] = {"0.23", "0.27", "0.30", "0.38", "0.47", "0.55",
        "0.66", "0.82", "1.04", "1.28", "1.50", "1.80", "2.25", "2.80",
        "3.30", "4.00", "5.00", "6.20", "7.20"};
    char* gbp_real = argv[3];
    unsigned short gbp = (unsigned short) get_index_str(gbp_dict, 19, gbp_real);

    // Set gain bandwidth product
    MA_write_GBP(channel, &error, gbp);
    errorout(error);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    // Output message so it can be read by SSH connection
    cout << "DONE" << endl;
    cout << flush;

    return 0;
}
