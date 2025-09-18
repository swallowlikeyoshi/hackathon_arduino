#ifndef GPSDATA_H
#define GPSDATA_H

#include <SoftwareSerial.h>
#include <TinyGPSPlus.h>

class GPSdata {
private:
    const int rxPin;
    const int txPin;
    SoftwareSerial ss;
    TinyGPSPlus gps;

public:
    GPSdata(int rx, int tx) : rxPin(rx), txPin(tx), ss(rx, tx) {}

    bool begin(long baud = 9600) {
        return ss.begin(baud);
    }

    void update() {
        while (ss.available() > 0) {
            gps.encode(ss.read());
        }
    }

    bool locationUpdated() {
        return gps.location.isUpdated();
    }

    double latitude() {
        return gps.location.lat();
    }

    double longitude() {
        return gps.location.lng();
    }
};

#endif // GPSDATA_H