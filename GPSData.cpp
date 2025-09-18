#include "GPSdata.h"

bool GPSdata::begin(long baud) {
    return ss.begin(baud);
}

void GPSdata::update() {
    while (ss.available() > 0) {
        gps.encode(ss.read());
    }
}

bool GPSdata::locationUpdated() {
    return gps.location.isUpdated();
}

double GPSdata::latitude() {
    return gps.location.lat();
}

double GPSdata::longitude() {
    return gps.location.lng();
}