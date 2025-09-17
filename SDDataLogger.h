#ifndef SDDATALOGGER_H
#define SDDATALOGGER_H

#include <SD.h>
#include <Arduino.h>

// Arduino Uno SPI pins
// SCK : 13
// MISO: 12
// MOSI: 11

class SDDataLogger {
private:
    uint8_t chipSelect;
    String fileName;
    File file;
    bool fileOpen;

public:
    SDDataLogger(uint8_t csPin) : chipSelect(csPin), fileOpen(false) {}

    bool begin(const String& fileName = "datalog.txt") {
        this->fileName = fileName;
        return SD.begin(chipSelect);
    }

    bool open(uint8_t mode = FILE_WRITE) {
        if (fileOpen) {
            file.close();
        }
        file = SD.open(fileName, mode);
        fileOpen = file ? true : false;
        return fileOpen;
    }

    bool setFileName(const String& fileName) {
        if (fileOpen) {
            file.close();
            fileOpen = false;
        }
        this->fileName = fileName;
        return open();
    }

    bool log(const String& data) {
        if (fileOpen && file) {
            file.println(data);
            file.flush();
            return true;
        }
        return false;
    }

    void close() {
        if (fileOpen && file) {
            file.close();
            fileOpen = false;
        }
    }

    ~SDDataLogger() {
        close();
    }
};

#endif // SDDATALOGGER_H