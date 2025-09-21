#include "SDDataLogger.h"

SDDataLogger::SDDataLogger(uint8_t csPin)
    : chipSelect(csPin), fileOpen(false) {}

bool SDDataLogger::begin() {
    this->fileName = "datalog_" + String(fileCount) + ".txt";
    return SD.begin(chipSelect);
}

bool SDDataLogger::open(uint8_t mode) {
    if (fileOpen) {
        file.close();
    }
    file = SD.open(fileName, mode);
    fileOpen = file ? true : false;
    Serial.println("file status: " + String(fileOpen ? "opened" : "failed to open"));
    return fileOpen;
}

bool SDDataLogger::setFileName(const String& filePrefix) {
    if (fileOpen) {
        file.close();
        fileOpen = false;
    }
    this->filePrefix = filePrefix;
    this->fileName = filePrefix + String(fileCount) + ".txt";
    if (open(FILE_WRITE)) {
        logCount = 0; // Reset log count for new file
        return true;
    }

    return false;
}

bool SDDataLogger::log(const String& data) {
    if (logCount >= MAX_LOG_ENTRIES) {
        fileCount++;
        String newFileName = filePrefix + String(fileCount) + ".txt";
        this->fileName = newFileName;
        if (open(FILE_WRITE)) {
            logCount = 0;
            file.println(fileName + " Log Start");
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