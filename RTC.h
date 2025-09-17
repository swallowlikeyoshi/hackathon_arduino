#ifndef RTC_H
#define RTC_H

#include <WiFi.h>
#include <WiFiUdp.h>
#include <NTPClient.h>

class RTC {
private:
    WiFiUDP ntpUDP;
    NTPClient timeClient;
    bool initialized;
    const char* ssid;
    const char* password;

public:
    RTC(const char* ssid, const char* password, long gmtOffset = 0, int updateInterval = 60000)
        : ssid(ssid), password(password), timeClient(ntpUDP, "pool.ntp.org", gmtOffset, updateInterval), initialized(false)
    {}

    bool begin()
    {
        WiFi.begin(ssid, password);
        while (WiFi.status() != WL_CONNECTED) {
            delay(500);
        }
        timeClient.begin();
        timeClient.update();
        initialized = true;
        return initialized;
    }

    bool isInitialized() const {
        return initialized;
    }

    void update() {
        timeClient.update();
    }

    String getFormattedTime() {
        return timeClient.getFormattedTime();
    }

    unsigned long getEpochTime() {
        return timeClient.getEpochTime();
    }

    int getHours() {
        return timeClient.getHours();
    }

    int getMinutes() {
        return timeClient.getMinutes();
    }

    int getSeconds() {
        return timeClient.getSeconds();
    }
};

#endif // RTC_H