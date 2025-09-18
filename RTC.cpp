#include "RTC.h"

#include "env.h"

RTC::RTC(const char* ssid, const char* password, long gmtOffset, int updateInterval)
    : ssid(ssid),
      password(password),
      timeClient(ntpUDP, "pool.ntp.org", gmtOffset, updateInterval),
      initialized(false)
{}

bool RTC::begin() {
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
    }
    timeClient.begin();
    timeClient.update();
    initialized = true;
    return initialized;
}

bool RTC::isInitialized() const {
    return initialized;
}

void RTC::update() {
    timeClient.update();
}

String RTC::getFormattedTime() {
    return timeClient.getFormattedTime();
}

unsigned long RTC::getEpochTime() {
    return timeClient.getEpochTime();
}

int RTC::getHours() {
    return timeClient.getHours();
}

int RTC::getMinutes() {
    return timeClient.getMinutes();
}

int RTC::getSeconds() {
    return timeClient.getSeconds();
}

int RTC::getYear() {
    time_t rawTime = (time_t)getEpochTime();
    struct tm* timeinfo = localtime(&rawTime);
    return timeinfo->tm_year + 1900;
}

int RTC::getMonth() {
    time_t rawTime = (time_t)getEpochTime();
    struct tm* timeinfo = localtime(&rawTime);
    return timeinfo->tm_mon + 1;
}

int RTC::getDay() {
    time_t rawTime = (time_t)getEpochTime();
    struct tm* timeinfo = localtime(&rawTime);
    return timeinfo->tm_mday;
}

String RTC::getFormattedDateTime() {
    time_t rawTime = (time_t)getEpochTime();
    struct tm* timeinfo = localtime(&rawTime);

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