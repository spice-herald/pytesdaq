#include <iostream>
#include <time.h>
#include <thread>
#include <chrono>
#include <string>
#include "magsv.h"
#include "sc_functions.cpp"

using namespace std;

int main(int argc, char** argv) {

    // Check arguments
    if (argc != 3 && argc != 5) {
        cout << "ERROR: run the program as follows" << endl;
        cout << "\t.\\get_channel_info.exe channel[1,2,3] active[0,1] [baud = 57600] [timeout = 100]" << endl;
        cout << "\tNote: either set both baud and timeout or neither." << endl;
        cout << "\tNote: active indicates whether to make the channel the active channel." << endl;
        cout << flush;
        return 1;
    }

    // Set connection info
    unsigned short error = 0;
    unsigned long baud = 57600, timeout = 100; 
    if (argc == 5) {
        baud = stoul(argv[3]);
        timeout = stoul(argv[4]);
    }

    // Set user-defined arguments and other necessary containers
    unsigned short channel = (unsigned short)(stoul(argv[1]));
    unsigned short active = (unsigned short)(stoul(argv[2]));
    unsigned short type_id, version_id, board_id, case_id;

    // Connect to electronics
    MA_initUSB(&error, baud, timeout);
    errorout(error);

    // Set active channel if desired
    if (active == 1) {
        MA_SetActiveChannel(channel, &error);
        errorout(error);
    }

    // Get channel info
    MA_channelInfo(channel, &error, &type_id, &version_id, &board_id, &case_id);
    errorout(error);
    printf("SUCCESS: Type ID: %d   Version ID: %d   Board ID: %d   Case ID: %d\n",
        type_id, version_id, board_id, case_id);

    // Close connection
    MA_closeUSB(&error);
    errorout(error);

    return 0;
}
