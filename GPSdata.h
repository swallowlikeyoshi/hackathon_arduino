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

    bool begin(long);
    void update();
    bool locationUpdated();
    double latitude();
    double longitude();
};

#endif // GPSDATA_H