import serial
import time
import math
import numpy as np
from vpython import box, vector, rate, scene

# ====== 시리얼 포트 설정 ======
ser = serial.Serial('/dev/cu.usbmodem1051DB2BD6FC2', 115200, timeout=1)
time.sleep(2)

# ====== VPython 3D 모델 ======
cube = box(length=0.1, height=0.2, width=0.5, color=vector(0,0,1))

# ====== 필터 파라미터 ======
alpha = 0.98  # complementary filter 계수
dt = 0.1      # 샘플링 주기 (1/10초 = 0.1초)

# 초기화
roll, pitch, yaw = 0.0, 0.0, 0.0

def reset(evt):
    global roll, pitch, yaw
    roll, pitch, yaw = 0.0, 0.0, 0.0
    print("Orientation reset to zero.")

scene.bind('keydown', lambda evt: reset(evt) if evt.key == 'r' else None)

while True:
    rate(10)  # 초당 10번 업데이트
    
    line = ser.readline().decode('utf-8').strip()
    if not line:
        continue
    
    try:
        ax, ay, az, gx, gy, gz, mx, my, mz = map(float, line.split())
    except:
        continue
    
    # ----- 가속도 기반 Roll, Pitch 계산 -----
    accel_roll = math.atan2(ay, az) * 180 / math.pi
    accel_pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2)) * 180 / math.pi
    
    # ----- 자력계 기반 Yaw 계산 -----
    yaw_mag = math.degrees(math.atan2(my, mx))
    
    # ----- Complementary Filter -----
    roll = alpha * (roll + gx * dt) + (1 - alpha) * accel_roll
    pitch = alpha * (pitch + gy * dt) + (1 - alpha) * accel_pitch
    yaw = alpha * (yaw + gz * dt) + (1 - alpha) * yaw_mag
    
    # ----- 3D 모델 회전 -----
    roll_rad = math.radians(roll)
    pitch_rad = math.radians(pitch)
    yaw_rad = math.radians(yaw)

    Rx = np.array([[1, 0, 0],
                   [0, math.cos(roll_rad), -math.sin(roll_rad)],
                   [0, math.sin(roll_rad),  math.cos(roll_rad)]])
    
    Ry = np.array([[ math.cos(pitch_rad), 0, math.sin(pitch_rad)],
                   [0, 1, 0],
                   [-math.sin(pitch_rad), 0, math.cos(pitch_rad)]])
    
    Rz = np.array([[math.cos(yaw_rad), -math.sin(yaw_rad), 0],
                   [math.sin(yaw_rad),  math.cos(yaw_rad), 0],
                   [0, 0, 1]])
    
    R = Rz @ Ry @ Rx
    
    cube.axis = vector(R[0,0], R[1,0], R[2,0])   # local x축
    cube.up   = vector(R[0,1], R[1,1], R[2,1])   # local y축