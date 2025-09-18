#include "SDDataLogger.h"

SDDataLogger::SDDataLogger(uint8_t csPin)
    : chipSelect(csPin), fileOpen(false) {}

bool SDDataLogger::begin(const String& fileName) {
    this->fileName = fileName;
    return SD.begin(chipSelect);
}

bool SDDataLogger::open(uint8_t mode) {
    if (fileOpen) {
        file.close();
    }
    file = SD.open(fileName, mode);
    fileOpen = file ? true : false;
    return fileOpen;
}

bool SDDataLogger::setFileName(const String& fileName) {
    if (fileOpen) {
        file.close();
        fileOpen = false;
    }
    this->fileName = fileName;
    return open();
}

bool SDDataLogger::log(const String& data) {
    if (fileOpen && file) {
        file.println(data);
        file.flush();
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