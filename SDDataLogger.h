#ifndef SDDATALOGGER_H
#define SDDATALOGGER_H

#include "env.h"
#include <SD.h>
#include <Arduino.h>

class SDDataLogger {
private:
    uint8_t chipSelect;
    String filePrefix = "datalog_";
    String fileName = "default.txt";
    File file;
    bool fileOpen;
    int logCount = 0;
    int fileCount = 0;

public:
    SDDataLogger(uint8_t csPin);

    bool begin();
    bool open(uint8_t mode = FILE_WRITE);
    bool setFileName(const String& fileName);
    bool setFilePrefix(const String& filePrefix);
    bool log(const String& data);
    void close();

    ~SDDataLogger();
};

#endif // SDDATALOGGER_H