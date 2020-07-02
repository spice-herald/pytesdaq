#include <iostream>
#include <time.h>
#include <thread>
#include <chrono>
#include <string>
#include "magsv.h"

using namespace std;

const double IB_MIN = 0., IB_MAX = 180.;
const double VB_MIN = 0., VB_MAX = 1300.;
const double PHIB_MIN = -125., PHIB_MAX = 125.;
const double IAUX_LOW_MIN = -125., IAUX_LOW_MAX = 125.;
const double IAUX_HIGH_MIN = -500., IAUX_HIGH_MAX = 500.;

void errorout(unsigned short error) {
    if (error != 0)
        cout << "\nCommunication Error" << endl;
}

