#include "env.h"

#include "GPSdata.h"
#include "SDDataLogger.h"
#include "MotionData.h"
// #include "RTC.h"

GPSdata gpsData(GPS_RX_PIN, GPS_TX_PIN);
SDDataLogger sdLogger(SD_CS_PIN);
MotionData motionData(MPU9250_CS_PIN);
// RTC rtc("KT_GiGA_8C65", "0ac27xf296", 9 * 3600); // GMT+9

void setup() {
    delay(3000); // For serial monitor connection

    Serial.begin(115200);
    Serial.println("******** Setup Start ********");

    bool success = true;
    
    if (gpsData.begin(GPS_BAUD, RTC_OFFSET)) {
        Serial.println("GPS initialized.");
    }
    else {
        Serial.println("GPS initialization failed!");
        success = false;
    }

    if (motionData.begin()) {
        Serial.println("MPU9250 initialized.");
    }
    else {
        Serial.println("MPU9250 initialization failed!");
        success = false;
    }

    if (sdLogger.begin()) {
        Serial.println("SD card initialized.");
    }
    else {
        Serial.println("SD card initialization failed!");
        success = false;
    }

    // if (rtc.begin()) {
    //     Serial.println("RTC initialized and time synchronized.");
    // }
    // else {
    //     Serial.println("RTC initialization failed!");
    //     success = false;
    // }

    // if (!success) {
    //     Serial.println("One or more components failed to initialize. Check connections and try again.");
    //     while (1); // Halt
    // }

    Serial.println("******** Setup Complete ********");
}

void loop() {
    Serial.println();

    gpsData.update();
    // gps 데이터가 준비될 때 까지 기다렸다가, 준비되면 시리얼로 출력하고 넘어가기
    while (!gpsData.locationUpdated()) {
        gpsData.update();
    }
    Serial.print("Latitude= ");
    Serial.print(gpsData.latitude(), 6);
    Serial.print(" Longitude= ");
    Serial.println(gpsData.longitude(), 6);

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

    // // Get current time from RTC
    // rtc.update();
    // Serial.print("Current Time: ");
    // Serial.println(rtc.getFormattedTime());

    sdLogger.open();
    String logEntry = gpsData.getFormattedDateTime() + "," + 
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

    // delay(1000);
}