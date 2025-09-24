import serial
import time
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import collections

# 시리얼 포트와 속도 설정
SERIAL_PORT = "/dev/cu.usbmodem1051DB2BD6FC2"  # 환경에 맞게 수정
BAUD_RATE = 115200

# 버퍼 크기 (최근 100개 값만 표시)
BUFFER_SIZE = 100

# 시리얼 초기화
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)

# 데이터 저장용 deque (고정 길이 큐)
accelX_data = collections.deque(maxlen=BUFFER_SIZE)
accelY_data = collections.deque(maxlen=BUFFER_SIZE)
accelZ_data = collections.deque(maxlen=BUFFER_SIZE)
gyroX_data = collections.deque(maxlen=BUFFER_SIZE)
gyroY_data = collections.deque(maxlen=BUFFER_SIZE)
gyroZ_data = collections.deque(maxlen=BUFFER_SIZE)
magX_data = collections.deque(maxlen=BUFFER_SIZE)
magY_data = collections.deque(maxlen=BUFFER_SIZE)
magZ_data = collections.deque(maxlen=BUFFER_SIZE)

# 초기화
for _ in range(BUFFER_SIZE):
    accelX_data.append(0)
    accelY_data.append(0)
    accelZ_data.append(0)
    gyroX_data.append(0)
    gyroY_data.append(0)
    gyroZ_data.append(0)
    magX_data.append(0)
    magY_data.append(0)
    magZ_data.append(0)

# 그래프 준비 - 3개로 분리
# 1. 가속도계 Figure
fig_accel, ax_accel = plt.subplots()
lineX, = ax_accel.plot([], [], label="accelX")
lineY, = ax_accel.plot([], [], label="accelY")
lineZ, = ax_accel.plot([], [], label="accelZ")
ax_accel.set_ylim(-2, 2)   # 가속도 범위 (단위 g 기준)
ax_accel.set_xlim(0, BUFFER_SIZE)
ax_accel.set_xlabel("Samples")
ax_accel.set_ylabel("Acceleration (g)")
ax_accel.legend()
ax_accel.set_title("Real-time Accelerometer Data")

# 2. 자이로스코프 Figure
fig_gyro, ax_gyro = plt.subplots()
lineGyroX, = ax_gyro.plot([], [], label="gyroX")
lineGyroY, = ax_gyro.plot([], [], label="gyroY")
lineGyroZ, = ax_gyro.plot([], [], label="gyroZ")
ax_gyro.set_ylim(-500, 500)   # 자이로 범위 (예시값, 필요시 조정)
ax_gyro.set_xlim(0, BUFFER_SIZE)
ax_gyro.set_xlabel("Samples")
ax_gyro.set_ylabel("Gyroscope (deg/s)")
ax_gyro.legend()
ax_gyro.set_title("Real-time Gyroscope Data")

# 3. 자기장센서 Figure
fig_mag, ax_mag = plt.subplots()
lineMagX, = ax_mag.plot([], [], label="magX")
lineMagY, = ax_mag.plot([], [], label="magY")
lineMagZ, = ax_mag.plot([], [], label="magZ")
ax_mag.set_ylim(-100, 100)   # 자기장 범위 (예시값, 필요시 조정)
ax_mag.set_xlim(0, BUFFER_SIZE)
ax_mag.set_xlabel("Samples")
ax_mag.set_ylabel("Magnetometer (uT)")
ax_mag.legend()
ax_mag.set_title("Real-time Magnetometer Data")

# 업데이트 함수
def update(frame):
    line = ser.readline().decode("utf-8").strip()
    if line:
        values = line.split(",")
        if len(values) == 11:  # 데이터 개수 확인
            try:
                accelX = float(values[2])
                accelY = float(values[3])
                accelZ = float(values[4])
                gyroX = float(values[5])
                gyroY = float(values[6])
                gyroZ = float(values[7])
                magX = float(values[8])
                magY = float(values[9])
                magZ = float(values[10])

                accelX_data.append(accelX)
                accelY_data.append(accelY)
                accelZ_data.append(accelZ)
                gyroX_data.append(gyroX)
                gyroY_data.append(gyroY)
                gyroZ_data.append(gyroZ)
                magX_data.append(magX)
                magY_data.append(magY)
                magZ_data.append(magZ)

                # 그래프 갱신 - accel
                lineX.set_data(range(len(accelX_data)), accelX_data)
                lineY.set_data(range(len(accelY_data)), accelY_data)
                lineZ.set_data(range(len(accelZ_data)), accelZ_data)
                # 그래프 갱신 - gyro
                lineGyroX.set_data(range(len(gyroX_data)), gyroX_data)
                lineGyroY.set_data(range(len(gyroY_data)), gyroY_data)
                lineGyroZ.set_data(range(len(gyroZ_data)), gyroZ_data)
                # 그래프 갱신 - mag
                lineMagX.set_data(range(len(magX_data)), magX_data)
                lineMagY.set_data(range(len(magY_data)), magY_data)
                lineMagZ.set_data(range(len(magZ_data)), magZ_data)
            except ValueError:
                pass

    return (lineX, lineY, lineZ, lineGyroX, lineGyroY, lineGyroZ, lineMagX, lineMagY, lineMagZ)

# 애니메이션 실행
ani_accel = FuncAnimation(fig_accel, update, interval=100)
ani_gyro = FuncAnimation(fig_gyro, update, interval=100)
ani_mag = FuncAnimation(fig_mag, update, interval=100)
plt.show()