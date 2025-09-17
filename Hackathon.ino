#define SERIAL_BAUD 115200
#define GPS_BAUD 9600L
#define GPS_RX_PIN 3
#define GPS_TX_PIN 4 
#define SD_CS_PIN 10
#define MPU9250_CS_PIN 9

#define USE_SOFT_SPI

#include "GPSdata.h"
#include "SDDataLogger.h"
#include "MotionData.h"
#include "RTC.h"

GPSdata gpsData(GPS_RX_PIN, GPS_TX_PIN);
SDDataLogger sdLogger(SD_CS_PIN);
MotionData motionData(MPU9250_CS_PIN);
RTC rtc("KT_GiGA_8C65", "0ac27xf296", 9 * 3600); // GMT+9

void setup() {
    Serial.println("*** Setup Start ***");

    pinMode(SD_CS_PIN, OUTPUT);
    pinMode(MPU9250_CS_PIN, OUTPUT);

    Serial.begin(115200);
    gpsData.begin(GPS_BAUD);

    digitalWrite(MPU9250_CS_PIN, LOW);
    if (!motionData.begin()) {
        Serial.println("MPU9250 initialization failed!");
    }
    digitalWrite(MPU9250_CS_PIN, HIGH);

    delay(100);

    digitalWrite(SD_CS_PIN, LOW);
    if (!sdLogger.begin()) {
        Serial.println("SD card initialization failed!");
    }
    digitalWrite(SD_CS_PIN, HIGH);

    delay(100);

    if (!rtc.begin()) {
        Serial.println("RTC initialization failed!");
        while (1);
    }

    Serial.println("*** Setup Complete ***");
}

void loop() {
    Serial.println();

    gpsData.update();
    if (gpsData.locationUpdated()) {
        Serial.print("Latitude= ");
        Serial.print(gpsData.latitude(), 6);
        Serial.print(" Longitude= ");
        Serial.println(gpsData.longitude(), 6);
    }

    float ax, ay, az;
    motionData.readAccel(ax, ay, az);
    Serial.print("Accel: ");
    Serial.print(ax); Serial.print(", ");
    Serial.print(ay); Serial.print(", ");
    Serial.println(az);

    float gx, gy, gz;
    motionData.readGyro(gx, gy, gz);
    Serial.print("Gyro: ");
    Serial.print(gx); Serial.print(", ");
    Serial.print(gy); Serial.print(", ");
    Serial.println(gz);

    // Get current time from RTC
    rtc.update();
    Serial.print("Current Time: ");
    Serial.println(rtc.getFormattedTime());

    sdLogger.open();
    String logEntry = rtc.getFormattedDateTime() + "," + 
                      String(gpsData.latitude(), 6) + "," + 
                      String(gpsData.longitude(), 6) + "," +
                      String(ax) + "," + String(ay) + "," + String(az) + "," +
                      String(gx) + "," + String(gy) + "," + String(gz);
    if (sdLogger.log(logEntry)) {
        Serial.println("Logged to SD: " + logEntry);
    } else {
        Serial.println("Failed to log to SD");
    }
    sdLogger.close();

    delay(1000);
}