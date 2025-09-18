#ifndef SDDATALOGGER_H
#define SDDATALOGGER_H

#include "env.h"
#include <SD.h>
#include <Arduino.h>

class SDDataLogger {
private:
    uint8_t chipSelect;
    String fileName;
    File file;
    bool fileOpen;

public:
    SDDataLogger(uint8_t csPin);

    bool begin(const String& fileName = "datalog.txt");
    bool open(uint8_t mode = FILE_WRITE);
    bool setFileName(const String& fileName);
    bool log(const String& data);
    void close();

    ~SDDataLogger();
};

#endif // SDDATALOGGER_H