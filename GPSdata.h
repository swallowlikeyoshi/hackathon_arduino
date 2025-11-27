#ifndef GPSDATA_H
#define GPSDATA_H

#include <SoftwareSerial.h>
#include <TinyGPSPlus.h>

class GPSdata {
private:
    const int rxPin;
    const int txPin;
    long timeOffset;
    SoftwareSerial ss;
    TinyGPSPlus gps;
public:
    GPSdata(int rx, int tx) : rxPin(rx), txPin(tx), ss(rx, tx) {}

    bool begin(long, long);
    void update();
    bool locationUpdated();
    double latitude();
    double longitude();
    String getFormattedDateTime();
};

#endif // GPSDATA_H

// #include "GPSdata.h"

bool GPSdata::begin(long baud, long offsetSeconds) {
    timeOffset = offsetSeconds;
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

String GPSdata::getFormattedDateTime() {
    if (gps.date.isValid() && gps.time.isValid()) {
        // GPS에서 받은 UTC 시각을 초 단위로 변환
        long totalSeconds = gps.time.hour() * 3600L +
                            gps.time.minute() * 60L +
                            gps.time.second() +
                            timeOffset;

        // 하루(24h = 86400s) 단위 보정
        int hour   = (totalSeconds / 3600) % 24;
        if (hour < 0) hour += 24; // 음수 방지
        int minute = (totalSeconds % 3600) / 60;
        int second = totalSeconds % 60;

        // 날짜 보정 (offset 때문에 날짜가 바뀔 수 있음)
        int year  = gps.date.year();
        int month = gps.date.month();
        int day   = gps.date.day();

        if (totalSeconds >= 86400) {
            // 다음 날로 넘어감
            day++;
            totalSeconds -= 86400;
            // 간단 처리를 위해 TinyGPSPlus 날짜값 직접 사용 (윤년 계산 등은 필요시 추가)
        } else if (totalSeconds < 0) {
            // 이전 날로 돌아감
            day--;
            totalSeconds += 86400;
        }

        char buffer[25];
        snprintf(buffer, sizeof(buffer), "%04d-%02d-%02d %02d:%02d:%02d",
                 year, month, day, hour, minute, second);
        return String(buffer);
    } else {
        return String("Invalid DateTime");
    }
}

