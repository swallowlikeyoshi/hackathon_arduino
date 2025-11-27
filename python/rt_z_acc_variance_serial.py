# rt_z_acc_variance_serial.py

import serial  # pyserial 라이브러리 필요
import time
import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import csv
import datetime

# TkAgg 백엔드 설정
matplotlib.use('TkAgg')

# ---------------------------
# 설정 (사용자 환경에 맞게 수정 필수!)
# ---------------------------
COM_PORT = 'COM3'  # 윈도우: 'COM3', 'COM4' 등 / 맥,리눅스: '/dev/ttyUSB0' 등
BAUD_RATE = 115200

WINDOW_SIZE = 20
STEP_SIZE = 10
GRAPH_WIDTH = 100 

# 데이터 처리용 버퍼
buffer = deque(maxlen=WINDOW_SIZE + STEP_SIZE)

# 그래프 시각화용 버퍼
z_variances = deque(maxlen=GRAPH_WIDTH)
mean_pitches = deque(maxlen=GRAPH_WIDTH)

new_data_counter = 0

# --- 특징 추출 함수 (기존과 동일) ---
def compute_feature(window_df):
    df = window_df.copy()
    for col in ['ax', 'ay', 'az']:
        df[f'{col}_smooth'] = df[col].rolling(window=2).mean()
    df.dropna(inplace=True)
    if df.empty:
        return None, None
    z_acc_var = df['az_smooth'].var()
    pitch_y_rad = np.mean(np.arctan2(df['ax_smooth'], np.sqrt(df['ay_smooth']**2 + df['az_smooth']**2)))
    mean_pitch_absolute = np.abs(pitch_y_rad)
    return z_acc_var, mean_pitch_absolute

# --- 그래프 초기 설정 (기존과 동일) ---
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

line1, = ax1.plot([], [], 'o-', markersize=4, label='Z-axis Variance')
ax1.set_title("Real-time Sensor Features (Serial Communication)") # 제목 변경
ax1.set_ylabel("Z-axis Variance")
ax1.grid(True)
ax1.legend(loc='upper right')
ax1.set_xlim(0, GRAPH_WIDTH - 1)
ax1.set_ylim(0, 0.1) 

line2, = ax2.plot([], [], 'o-', color='red', markersize=4, label='Mean Pitch (Absolute)')
ax2.set_xlabel("Time Step (Recent data)")
ax2.set_ylabel("Mean Pitch (Radians)")
ax2.grid(True)
ax2.legend(loc='upper right')
ax2.set_xlim(0, GRAPH_WIDTH - 1)
ax2.set_ylim(0, 0.5)

fig.tight_layout()

# ---------------------------
# 시리얼 통신 및 메인 루프
# ---------------------------

# 시리얼 객체 초기화 변수
ser = None

try:
    print(f"🔌 {COM_PORT} 포트 연결 시도 중 ({BAUD_RATE}bps)...")
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.1)
    time.sleep(2) # 아두이노 리셋 대기
    ser.reset_input_buffer() # 쌓여있는 이전 데이터 삭제
    print("✅ 시리얼 연결 성공!")

    timestamp_start = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"sensor_log_serial_{timestamp_start}.csv"
    print(f"📝 데이터를 '{filename}' 파일에 저장합니다.")

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        header = ['lat','lon','ax','ay','az','gx','gy','gz','mx','my','mz', 'timestamp']
        writer.writerow(header)
        
        plt.show(block=False)
        fig.canvas.draw()

        while True:
            try:
                # 시리얼 데이터 한 줄 읽기
                if ser.in_waiting > 0:
                    # decode 오류 무시 (errors='ignore')하여 깨진 바이트로 인한 멈춤 방지
                    raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
                else:
                    # 데이터가 없으면 그래프 이벤트 처리 후 계속
                    fig.canvas.flush_events()
                    continue

                if not raw_line: continue
                
                # 디버그 메시지("MPU connected" 등) 걸러내기 및 파싱
                try:
                    frame_values = list(map(float, raw_line.split(',')))
                except ValueError:
                    # 숫자로 변환 안 되는 문자열(디버그 메시지 등)은 무시하고 출력만 해봄
                    # print(f"Info: {raw_line}") 
                    continue

                if len(frame_values) != 11:
                    continue
                
                # --- 이하 로직은 기존 UDP 코드와 동일 ---
                timestamp_now = datetime.datetime.now().isoformat()
                writer.writerow(frame_values + [timestamp_now])

                buffer.append(frame_values)
                new_data_counter += 1

                if new_data_counter >= STEP_SIZE and len(buffer) >= WINDOW_SIZE:
                    new_data_counter = 0
                    window_data = list(buffer)[-WINDOW_SIZE:]
                    df = pd.DataFrame(window_data, columns=header[:-1])
                    
                    z_var, pitch = compute_feature(df)
                    
                    if z_var is not None:
                        z_variances.append(z_var)
                        mean_pitches.append(pitch)
                        
                        line1.set_data(range(len(z_variances)), z_variances)
                        line2.set_data(range(len(mean_pitches)), mean_pitches)

                        fig.canvas.draw()
                        fig.canvas.flush_events()

            except Exception as e:
                print(f"오류 발생: {e}")
                break

except serial.SerialException as e:
    print(f"❌ 시리얼 포트 오류: {e}")
    print("포트 번호가 맞는지, 다른 프로그램(아두이노 시리얼 모니터 등)이 사용 중인지 확인하세요.")

except KeyboardInterrupt:
    print("\n🛑 프로그램을 종료합니다.")

finally:
    if ser is not None and ser.is_open:
        ser.close()
    print("시리얼 포트가 닫혔습니다.")