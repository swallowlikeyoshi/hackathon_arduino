#ifndef RTC_H
#define RTC_H

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

    // 날짜 정보 추가
    int getYear() {
        time_t rawTime = (time_t)getEpochTime();
        struct tm * timeinfo = localtime(&rawTime);
        return timeinfo->tm_year + 1900;
    }

    int getMonth() {
        time_t rawTime = (time_t)getEpochTime();
        struct tm * timeinfo = localtime(&rawTime);
        return timeinfo->tm_mon + 1;
    }

    int getDay() {
        time_t rawTime = (time_t)getEpochTime();
        struct tm * timeinfo = localtime(&rawTime);
        return timeinfo->tm_mday;
    }

    // 날짜와 시간 포맷으로 문자열 반환 (YYYY-MM-DD HH:MM:SS)
    String getFormattedDateTime() {
        time_t rawTime = (time_t)getEpochTime();
        struct tm * timeinfo = localtime(&rawTime);

        char buffer[20];
        snprintf(buffer, sizeof(buffer), "%04d-%02d-%02d %02d:%02d:%02d",
                 timeinfo->tm_year + 1900,
                 timeinfo->tm_mon + 1,
                 timeinfo->tm_mday,
                 timeinfo->tm_hour,
                 timeinfo->tm_min,
                 timeinfo->tm_sec);
        return String(buffer);
    }
};

#endif // RTC_H