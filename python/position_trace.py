import serial
import time
import math
import numpy as np
from vpython import box, vector, rate, scene, text
from collections import deque

# ====== 시리얼 포트 설정 ======
ser = serial.Serial('/dev/cu.usbmodem1051DB2BD6FC2', 115200, timeout=1)
time.sleep(2)

# ====== VPython 3D 모델 ======
cube = box(length=0.1, height=0.2, width=0.5, color=vector(0,0,1))

# ====== 필터 파라미터 ======
alpha = 0.98  # complementary filter 계수
dt = 0.1      # 샘플링 주기 (1/10초 = 0.1초)
window_size = 5  # 이동평균 필터 윈도우 크기

# 이동평균 필터용 큐 초기화
ax_queue = deque(maxlen=window_size)
ay_queue = deque(maxlen=window_size)
az_queue = deque(maxlen=window_size)
gx_queue = deque(maxlen=window_size)
gy_queue = deque(maxlen=window_size)
gz_queue = deque(maxlen=window_size)
mx_queue = deque(maxlen=window_size)
my_queue = deque(maxlen=window_size)
mz_queue = deque(maxlen=window_size)

# 초기화
roll, pitch, yaw = 0.0, 0.0, 0.0

# Heading 텍스트 초기화 (cube 위쪽에 위치)
heading_text = text(text='Heading: 0.0°', pos=cube.pos + vector(0, 0.3, 0), height=0.1, color=vector(1,1,1), billboard=True, emissive=True)

def reset(evt):
    global roll, pitch, yaw
    roll, pitch, yaw = 0.0, 0.0, 0.0
    print("Orientation reset to zero.")

scene.bind('keydown', lambda evt: reset(evt) if evt.key == 'r' else None)

while True:

    # 시리얼 버퍼 비우기
    ser.reset_input_buffer()

    rate(9)  # 초당 10번 업데이트
    
    line = ser.readline().decode('utf-8').strip()
    if not line:
        continue
    
    try:
        ax, ay, az, gx, gy, gz, mx, my, mz = map(float, line.split())
    except:
        continue
    
    # 이동평균 필터에 데이터 추가
    ax_queue.append(ax)
    ay_queue.append(ay)
    az_queue.append(az)
    gx_queue.append(gx)
    gy_queue.append(gy)
    gz_queue.append(gz)
    mx_queue.append(mx)
    my_queue.append(my)
    mz_queue.append(mz)
    
    # 이동평균 계산
    ax_avg = sum(ax_queue) / len(ax_queue)
    ay_avg = sum(ay_queue) / len(ay_queue)
    az_avg = sum(az_queue) / len(az_queue)
    gx_avg = sum(gx_queue) / len(gx_queue)
    gy_avg = sum(gy_queue) / len(gy_queue)
    gz_avg = sum(gz_queue) / len(gz_queue)
    mx_avg = sum(mx_queue) / len(mx_queue)
    my_avg = sum(my_queue) / len(my_queue)
    mz_avg = sum(mz_queue) / len(mz_queue)
    
    # ----- 가속도 기반 Roll, Pitch 계산 -----
    accel_roll = math.atan2(ay_avg, az_avg) * 180 / math.pi
    accel_pitch = math.atan2(-ax_avg, math.sqrt(ay_avg**2 + az_avg**2)) * 180 / math.pi
    
    # ----- 자력계 기반 Yaw 계산 -----
    yaw_mag = math.degrees(math.atan2(my_avg, mx_avg))
    
    # ----- Complementary Filter -----
    roll = alpha * (roll + gx_avg * dt) + (1 - alpha) * accel_roll
    pitch = alpha * (pitch + gy_avg * dt) + (1 - alpha) * accel_pitch
    yaw = alpha * (yaw + gz_avg * dt) + (1 - alpha) * yaw_mag
    
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

    # 자력계 데이터를 사용하여 지표면 기준 heading(북 기준 각도) 계산
    # 보정된 heading은 yaw_mag 값이며, 0~360도 범위로 변환
    heading = yaw_mag
    if heading < 0:
        heading += 360

    # VPython 화면에 heading 텍스트 업데이트 (cube 위쪽)
    heading_text.text = f'Heading: {heading:.1f}°'
    heading_text.pos = cube.pos + vector(0, 0.3, 0)