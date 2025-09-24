#include "SDDataLogger.h"
#include <SD.h>

SDDataLogger::SDDataLogger(uint8_t csPin)
    : chipSelect(csPin), fileOpen(false) {}

bool SDDataLogger::begin() {
    return SD.begin(chipSelect);
}

bool SDDataLogger::open(uint8_t mode) {
    if (fileOpen) {
        file.close();
    }
    // Construct short filename with 8.3 format
    String shortName = filePrefix + String(fileCount) + ".txt";
    if (shortName.length() > 12) {
        shortName = shortName.substring(0, 8) + ".txt";
    }
    file = SD.open(shortName.c_str(), mode);
    fileOpen = file ? true : false;
    // Serial.println("file status: " + String(fileOpen ? "opened" : "failed to open"));
    return fileOpen;
}

bool SDDataLogger::setFileName(const String& filePrefix) {
    if (fileOpen) {
        file.close();
        fileOpen = false;
    }
    this->filePrefix = filePrefix;
    // if (open(FILE_WRITE)) 
    //     logCount = 0; // Reset log count for new file
    //     return true;
    // }
    return true;
}

bool SDDataLogger::log(const String& data) {
    if (logCount >= MAX_LOG_ENTRIES) {
        fileCount++;
        // Construct new filename with 8.3 format
        String newFileName = filePrefix + String(fileCount) + ".txt";
        if (newFileName.length() > 12) {
            newFileName = newFileName.substring(0, 8) + ".txt";
        }
        if (open(FILE_WRITE)) {
            logCount = 0;
            file.println(filePrefix + " Log Start");
            file.flush();
        }
    }
    if (fileOpen && file) {
        file.println(data);
        file.flush();
        logCount++;
        return true;
    }
    return false;
}

void SDDataLogger::close() {
    if (fileOpen && file) {
        file.close();
        fileOpen = false;
    }
}

SDDataLogger::~SDDataLogger() {
    close();
}