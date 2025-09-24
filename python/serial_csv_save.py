import serial
import csv
import time

# 시리얼 포트와 속도 설정
SERIAL_PORT = "/dev/cu.usbmodem1051DB2BD6FC2"  # 예: Windows는 "COM3", Mac은 "/dev/tty.usbmodemXXXX"
BAUD_RATE = 115200

# 저장할 CSV 파일 이름
CSV_FILE = "sensor_data.csv"

def main():
    # 시리얼 포트 열기
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # 시리얼 안정화 대기

    # CSV 파일 열기
    with open(CSV_FILE, mode="w", newline="") as file:
        writer = csv.writer(file)

        # 헤더 작성
        header = ["latitude", "longitude",
                  "accelX", "accelY", "accelZ",
                  "gyroX", "gyroY", "gyroZ",
                  "magX", "magY", "magZ"]
        writer.writerow(header)

        print("데이터 수집 시작... (Ctrl+C로 종료)")

        try:
            while True:
                line = ser.readline().decode("utf-8").strip()
                if line:
                    values = line.split(",")
                    if len(values) == 11:
                        writer.writerow(values)
                        file.flush()
                        print(values)
        except KeyboardInterrupt:
            print("데이터 수집 종료")

    ser.close()

if __name__ == "__main__":
    main()