#ifndef RTC_H
#define RTC_H

#include "env.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include <NTPClient.h>
#include <time.h>

class RTC {
private:
    WiFiUDP ntpUDP;
    NTPClient timeClient;
    bool initialized;
    const char* ssid;
    const char* password;

public:
    RTC(const char* ssid, const char* password, long gmtOffset = 0, int updateInterval = 60000);

    bool begin();
    bool isInitialized() const;

    void update();

    String getFormattedTime();
    unsigned long getEpochTime();

    int getHours();
    int getMinutes();
    int getSeconds();

    int getYear();
    int getMonth();
    int getDay();

    String getFormattedDateTime();
};

#endif // RTC_H