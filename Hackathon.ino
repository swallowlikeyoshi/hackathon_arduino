#include "env.h"

#include "GPSdata.h"
#include "SDDataLogger.h"
#include "MotionData.h"
// #include "RTC.h"


GPSdata gpsData(GPS_RX_PIN, GPS_TX_PIN);
SDDataLogger sdLogger(SD_CS_PIN);
MotionData motionData(MPU9250_CS_PIN);
// RTC rtc("KT_GiGA_8C65", "0ac27xf296", 9 * 3600); // GMT+9
bool isGPSInitialized = false;

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
        float bias[6];
        motionData.readCalibration(bias);
        Serial.print("Accel Bias: ");
        Serial.print(bias[0]); Serial.print(", ");
        Serial.print(bias[1]); Serial.print(", ");
        Serial.println(bias[2]);
        Serial.print("Gyro Bias: ");
        Serial.print(bias[3]); Serial.print(", ");
        Serial.print(bias[4]); Serial.print(", ");
        Serial.println(bias[5]);
    }
    else {
        Serial.println("MPU9250 initialization failed!");
        success = false;
    }

    if (sdLogger.begin()) {
        // String safePrefix = gpsData.getFormattedDateTime().substring(0, 16);
        // safePrefix.replace(":", "-");
        // safePrefix.replace(" ", "_");
        // String filePrefix = safePrefix + "_log_";
        // Serial.println("Setting SD file prefix to: " + filePrefix);
        String filePrefix = "log";
        sdLogger.setFileName(filePrefix);
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

    if (!success) {
        Serial.println("One or more components failed to initialize. Check connections and try again.");
        while (1) {
            delay(100000);
        } // Halt
    }

    Serial.println("******** Setup Complete ********");
}

void loop() {
    Serial.println();

    gpsData.update();
    // gps 데이터가 준비될 때 까지 기다렸다가, 준비되면 시리얼로 출력하고 넘어가기
    // GPS는 1초에 한번씩 업데이트 되는데, 이를 기다리면 공백이 너무 커지게 된다.
    if (!isGPSInitialized) {
        while (!gpsData.locationUpdated()) {
            Serial.println("Waiting for GPS location...");
            gpsData.update();
            delay(1000);
        }
        isGPSInitialized = true;
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

    Serial.print("Current Time: ");
    Serial.println(gpsData.getFormattedDateTime()); // YYYY-MM-DD HH:MM:SS

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
        sdLogger.begin(); // Reinitialize SD card if logging fails
    }

    sdLogger.close();

    delay(1000); // 1초당 10회 루프
}