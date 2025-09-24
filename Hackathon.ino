/***************************************************************************
* Example sketch for the MPU9250_WE library
*
* This sketch shows how to get acceleration, gyroscocope, magnetometer and 
* temperature data from the MPU9250 using SPI.
* 
* For further information visit my blog:
*
* https://wolles-elektronikkiste.de/mpu9250-9-achsen-sensormodul-teil-1  (German)
* https://wolles-elektronikkiste.de/en/mpu9250-9-axis-sensor-module-part-1  (English)
* 
***************************************************************************/
#include "env.h"

#include "GPSdata.h"

#include <WiFi.h>
#include <MPU9250_WE.h>

#define READOUT_DELAY 20 // about 50 Hz

const char* ssid = "KT_GiGA_8C65";
const char* password = "0ac27xf296";
const char* server = "172.30.1.52";
const int port = 65000;
WiFiClient client;

const int csPin = 10;  // Chip Select Pin
// const int mosiPin = 22;  // "MOSI" Pin
// const int misoPin = 21;  // "MISO" Pin
// const int sckPin = 16;  // SCK Pin
bool useSPI = true;    // SPI use flag

/* There are two constructors for SPI: */
MPU9250_WE myMPU9250 = MPU9250_WE(&SPI, csPin, useSPI);

GPSdata gpsData(GPS_RX_PIN, GPS_TX_PIN);

/* Use this one if you want to change the default SPI pins (only for ESP32 / STM32 so far): */
// MPU9250_WE myMPU9250 = MPU9250_WE(&SPI, csPin, mosiPin, misoPin, sckPin, useSPI);

/* Changing SPI pins on STM32 boards can be a bit diffcult - the following worked on a Nucleo-L432KC board:

    const int csPin = D3;   
    const int mosiPin = A6; 
    const int misoPin = D10; 
    const int sckPin = A1;
    bool useSPI = true;    // SPI use flag
    MPU9250_WE myMPU9250 = MPU9250_WE(&SPI, csPin, mosiPin, misoPin, sckPin, useSPI);

   Or, using the same pins:
    SPIClass mySPI(mosiPin, misoPin, sckPin); // don't pass the CS-Pin (=SSEL)
    MPU9250_WE myMPU9250 = MPU9250_WE(&mySPI, csPin, useSPI);
*/

void setup() {
  
  Serial.begin(115200);
  // MAC 주소 출력
  Serial.print("MAC address: ");

  uint8_t macAddr[6];
  WiFi.macAddress(macAddr);
  for (int i = 0; i < 6; i++)
  {
    Serial.print(macAddr[i], HEX); Serial.print(":");
  }
  Serial.println();
  
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(1000);
    Serial.println("Connecting WiFi...");
  }
  delay(2000);
  Serial.println("WiFi Connected!");
  Serial.println(WiFi.localIP());

  if (client.connect(server, port)) {
    Serial.println("Connected to Python server!");
  } else {
    Serial.println("Connection failed.");
  }

  gpsData.begin(GPS_BAUD, RTC_OFFSET);

  if(!myMPU9250.init()){
    Serial.println("MPU9250 does not respond");
  }
  else{
    Serial.println("MPU9250 is connected");
  }
  if(!myMPU9250.initMagnetometer()){
    Serial.println("Magnetometer does not respond");
  }
  else{
    Serial.println("Magnetometer is connected");
  }

  /* Choose the SPI clock speed, default is 8 MHz 
     This function must be used only after init(), not before */
  //myMPU9250.setSPIClockSpeed(4000000);

  Serial.println("Position you MPU9250 flat and don't move it - calibrating...");
  delay(1000);
  myMPU9250.autoOffsets();
  Serial.println("Done!");
  
  //myMPU9250.setAccOffsets(-14240.0, 18220.0, -17280.0, 15590.0, -20930.0, 12080.0);
  //myMPU9250.setGyrOffsets(45.0, 145.0, -105.0);
  myMPU9250.enableGyrDLPF();
  //myMPU9250.disableGyrDLPF(MPU9250_BW_WO_DLPF_8800); // bandwdith without DLPF
  myMPU9250.setGyrDLPF(MPU9250_DLPF_6);
  myMPU9250.setSampleRateDivider(5);
  myMPU9250.setGyrRange(MPU9250_GYRO_RANGE_250);
  myMPU9250.setAccRange(MPU9250_ACC_RANGE_2G);
  myMPU9250.enableAccDLPF(true);
  myMPU9250.setAccDLPF(MPU9250_DLPF_6);
  //myMPU9250.enableAccAxes(MPU9250_ENABLE_XYZ);
  //myMPU9250.enableGyrAxes(MPU9250_ENABLE_XYZ);
  myMPU9250.setMagOpMode(AK8963_CONT_MODE_100HZ);
  delay(200);
}

void loop() {
  xyzFloat gValue = myMPU9250.getGValues();
  xyzFloat gyr = myMPU9250.getGyrValues();
  xyzFloat magValue = myMPU9250.getMagValues();
  float temp = myMPU9250.getTemperature();
  float resultantG = myMPU9250.getResultantG(gValue);

  // Serial.println("Acceleration in g (x,y,z):");
  // Serial.print(gValue.x);
  // Serial.print("   ");
  // Serial.print(gValue.y);
  // Serial.print("   ");
  // Serial.println(gValue.z);
  // Serial.print("Resultant g: ");
  // Serial.println(resultantG);

  // Serial.println("Gyroscope data in degrees/s: ");
  // Serial.print(gyr.x);
  // Serial.print("   ");
  // Serial.print(gyr.y);
  // Serial.print("   ");
  // Serial.println(gyr.z);

  // Serial.println("Magnetometer Data in µTesla: ");
  // Serial.print(magValue.x);
  // Serial.print("   ");
  // Serial.print(magValue.y);
  // Serial.print("   ");
  // Serial.println(magValue.z);

  // Serial.print("Temperature in °C: ");
  // Serial.println(temp);

  // Serial.println("********************************************");

  // gpsData.update();
  // Serial.print(gpsData.latitude(), 6); Serial.print(",");
  // Serial.print(gpsData.longitude(), 6); Serial.print(",");
  // Serial.print(gValue.x); Serial.print(",");
  // Serial.print(gValue.y); Serial.print(",");
  // Serial.print(gValue.z); Serial.print(",");
  // Serial.print(gyr.x); Serial.print(",");
  // Serial.print(gyr.y); Serial.print(",");
  // Serial.print(gyr.z); Serial.print(",");
  // Serial.print(magValue.x); Serial.print(",");
  // Serial.print(magValue.y); Serial.print(",");
  // Serial.print(magValue.z); Serial.print("\n");

  gpsData.update();

  String logString = String(gpsData.latitude(), 6) + "," +
                    String(gpsData.longitude(), 6) + "," +
                    gValue.x + "," +
                    gValue.y + "," +
                    gValue.z + "," +
                    gyr.x + "," +
                    gyr.y + "," +
                    gyr.z + "," +
                    magValue.x + "," +
                    magValue.y + "," +
                    magValue.z + "\n";

  if (client.connected())
  {
    client.print(logString);
    Serial.print("Send data to server: ");
    Serial.print(logString);
  }
  else
  {
    Serial.println("Disconnect from server.");
  }

  delay(READOUT_DELAY); // about 30 Hz
}
