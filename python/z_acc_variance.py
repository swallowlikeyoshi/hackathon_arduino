import socket
import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from matplotlib.animation import FuncAnimation
import csv
import datetime

# TkAgg 백엔드를 사용하여 GUI 창을 띄울 수 있도록 설정
matplotlib.use('TkAgg')

# ---------------------------
# 설정
# ---------------------------
# 아두이노 코드의 serverPort와 일치시켜야 함
UDP_PORT = 65001
HOST = '0.0.0.0'  # 모든 IP 주소에서 들어오는 데이터를 수신

WINDOW_SIZE = 20
STEP_SIZE = 10

# 최근 데이터 저장용 버퍼
buffer = deque(maxlen=WINDOW_SIZE + STEP_SIZE)
z_variances = []    # z_acc_variance 결과 저장
mean_pitches = []   # mean_pitch 결과 저장
new_data_counter = 0

# --- 특징 추출 및 그래프 관련 함수 (기존과 동일) ---

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

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
line1, = ax1.plot([], [], 'o-', label='Z-axis Variance')
ax1.set_title("Real-time Sensor Features")
ax1.set_ylabel("Z-axis Variance")
ax1.grid(True); ax1.legend(); ax1.set_ylim(0, 0.1)
line2, = ax2.plot([], [], 'o-', color='red', label='Mean Pitch (Absolute)')
ax2.set_xlabel("Feature Index")
ax2.set_ylabel("Mean Pitch (Radians)")
ax2.grid(True); ax2.legend(); ax2.set_ylim(0, 0.5)
fig.tight_layout()

def update(frame):
    if z_variances:
        xdata = list(range(len(z_variances)))
        line1.set_data(xdata, z_variances)
        ax1.set_xlim(0, max(50, len(z_variances) + 10))
        ax1.set_ylim(0, max(z_variances) * 1.2 + 0.01)
    if mean_pitches:
        xdata = list(range(len(mean_pitches))) # Ensure xdata is consistent
        line2.set_data(xdata, mean_pitches)
        ax2.set_ylim(0, max(mean_pitches) * 1.2 + 0.01)
    return line1, line2

ani = FuncAnimation(fig, update, interval=200, blit=True)

# ---------------------------
# UDP 서버 시작 (수정된 부분)
# ---------------------------
# UDP 소켓 생성
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, UDP_PORT))

print(f"✅ UDP 서버가 {UDP_PORT} 포트에서 수신 대기 중입니다...")

try:
    timestamp_start = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"sensor_log_{timestamp_start}.csv"
    print(f"📝 데이터를 '{filename}' 파일에 저장합니다.")

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # CSV 파일 헤더 작성
        header = ['lat','lon','ax','ay','az','gx','gy','gz','mx','my','mz', 'timestamp']
        writer.writerow(header)
        
        plt.show(block=False)
        fig.canvas.draw()

        while True:
            # UDP 데이터 수신
            raw_data, addr = sock.recvfrom(1024)
            
            # 수신 데이터 처리 (기존과 동일)
            try:
                data_line = raw_data.decode('utf-8').strip()
                if not data_line: continue
                
                frame_values = list(map(float, data_line.split(',')))
                if len(frame_values) != 11:
                    print(f"⚠️ 데이터 형식 오류, 건너뜁니다: {frame_values}")
                    continue
                
                timestamp_now = datetime.datetime.now().isoformat()
                full_frame = frame_values + [timestamp_now]
                writer.writerow(full_frame)

                buffer.append(frame_values)
                new_data_counter += 1

                if new_data_counter >= STEP_SIZE and len(buffer) >= WINDOW_SIZE:
                    new_data_counter = 0
                    window_data = list(buffer)[-WINDOW_SIZE:]
                    df = pd.DataFrame(window_data, columns=header[:-1]) # timestamp 제외
                    
                    z_var, pitch = compute_feature(df)
                    
                    if z_var is not None:
                        # print(f"New Features -> z_variance: {z_var:.4f}, mean_pitch: {pitch:.4f}")
                        z_variances.append(z_var)
                        mean_pitches.append(pitch)
                    
                    # 그래프 업데이트
                    fig.canvas.draw()
                    fig.canvas.flush_events()

            except (ValueError, IndexError) as e:
                print(f"데이터 파싱 오류: {e}")
                continue
            except Exception as e:
                print(f"알 수 없는 오류 발생: {e}")

except KeyboardInterrupt:
    print("\n🛑 서버를 종료합니다.")
finally:
    sock.close()
    print("소켓이 닫혔습니다.")