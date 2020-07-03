#include <iostream>
#include <string>
#include <limits>
#include "magsv.h"
#include "squid_control_helpers.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    unsigned short containers[3] = {(unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX, (unsigned short) USHRT_MAX};
    const char* extra_args[1] = {};
    validate_args(containers, argc, argv, "get_channel_info.exe", 0, extra_args);
    if (containers[0] == (unsigned short) USHRT_MAX) {
        return 1; }
    unsigned short channel = containers[0];
    unsigned short error = containers[2];

    // Get channel info
    unsigned short type_id, version_id, board_id, case_id;
    MA_channelInfo(channel, &error, &type_id, &version_id, &board_id, &case_id);
    errorout(error);
    printf("SUCCESS: Type ID: %d   Version ID: %d   Board ID: %d   Case ID: %d\n",
        type_id, version_id, board_id, case_id);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
