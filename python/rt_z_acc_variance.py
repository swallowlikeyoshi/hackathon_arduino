import socket
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
# 설정
# ---------------------------
UDP_PORT = 65001
HOST = '0.0.0.0'

WINDOW_SIZE = 20
STEP_SIZE = 10

# ★ 그래프에 보여줄 최대 점의 개수 (이 값을 조절하면 화면에 보이는 시간이 달라집니다)
GRAPH_WIDTH = 100 

# 데이터 처리용 버퍼 (특징 추출용)
buffer = deque(maxlen=WINDOW_SIZE + STEP_SIZE)

# ★ 그래프 시각화용 버퍼 (maxlen을 설정하여 오래된 데이터 자동 삭제)
z_variances = deque(maxlen=GRAPH_WIDTH)
mean_pitches = deque(maxlen=GRAPH_WIDTH)

new_data_counter = 0

# --- 특징 추출 함수 ---
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

# --- 그래프 초기 설정 ---
# FuncAnimation은 while True 루프와 충돌할 수 있어 제거하고, 수동 업데이트 방식 사용
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# 초기 빈 라인 생성
line1, = ax1.plot([], [], 'o-', markersize=4, label='Z-axis Variance')
ax1.set_title("Real-time Sensor Features (Sliding Window)")
ax1.set_ylabel("Z-axis Variance")
ax1.grid(True)
ax1.legend(loc='upper right')
# ★ X축을 고정합니다 (0 ~ GRAPH_WIDTH)
ax1.set_xlim(0, GRAPH_WIDTH - 1)
ax1.set_ylim(0, 0.1) 

line2, = ax2.plot([], [], 'o-', color='red', markersize=4, label='Mean Pitch (Absolute)')
ax2.set_xlabel("Time Step (Recent data)")
ax2.set_ylabel("Mean Pitch (Radians)")
ax2.grid(True)
ax2.legend(loc='upper right')
# ★ X축을 고정합니다
ax2.set_xlim(0, GRAPH_WIDTH - 1)
ax2.set_ylim(0, 0.5)

fig.tight_layout()

# ---------------------------
# UDP 서버 및 메인 루프
# ---------------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, UDP_PORT))
sock.settimeout(0.05) # ★ 소켓 타임아웃 설정 (그래프 반응성 향상을 위해 블로킹 방지)

print(f"✅ UDP 서버가 {UDP_PORT} 포트에서 수신 대기 중입니다...")

try:
    timestamp_start = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"sensor_log_{timestamp_start}.csv"
    print(f"📝 데이터를 '{filename}' 파일에 저장합니다.")

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        header = ['lat','lon','ax','ay','az','gx','gy','gz','mx','my','mz', 'timestamp']
        writer.writerow(header)
        
        # 그래프 창 띄우기
        plt.show(block=False)
        
        # 배경 저장 (블리팅 기법을 쓰고 싶다면 필요하지만, 여기선 단순 redraw 사용)
        fig.canvas.draw()

        while True:
            try:
                # UDP 데이터 수신 (타임아웃 설정으로 인해 데이터 없으면 예외 발생하고 루프 계속됨)
                try:
                    raw_data, addr = sock.recvfrom(1024)
                except socket.timeout:
                    # 데이터가 안 들어와도 그래프 창의 이벤트(창 닫기 등)를 처리하기 위해 업데이트
                    fig.canvas.flush_events() 
                    continue

                data_line = raw_data.decode('utf-8').strip()
                if not data_line: continue
                
                frame_values = list(map(float, data_line.split(',')))
                if len(frame_values) != 11:
                    continue
                
                timestamp_now = datetime.datetime.now().isoformat()
                writer.writerow(frame_values + [timestamp_now])

                buffer.append(frame_values)
                new_data_counter += 1

                # 일정 데이터가 모이면 특징 추출 및 그래프 업데이트
                if new_data_counter >= STEP_SIZE and len(buffer) >= WINDOW_SIZE:
                    new_data_counter = 0
                    window_data = list(buffer)[-WINDOW_SIZE:]
                    df = pd.DataFrame(window_data, columns=header[:-1])
                    
                    z_var, pitch = compute_feature(df)
                    
                    if z_var is not None:
                        # ★ deque에 데이터 추가 (오래된 데이터는 자동으로 밀려남)
                        z_variances.append(z_var)
                        mean_pitches.append(pitch)
                        
                        # ★ 그래프 데이터 업데이트
                        # x축 데이터는 항상 0, 1, ..., len-1 형태로 생성하여 '흐르는' 효과를 줌
                        line1.set_data(range(len(z_variances)), z_variances)
                        line2.set_data(range(len(mean_pitches)), mean_pitches)

                        # Y축 스케일 자동 조정 (선택 사항)
                        # 데이터가 튀었을 때 그래프 밖으로 나가는 것을 방지하고 싶다면 주석 해제
                        # if z_var > ax1.get_ylim()[1]: ax1.set_ylim(0, z_var * 1.5)
                        # if pitch > ax2.get_ylim()[1]: ax2.set_ylim(0, pitch * 1.5)

                        fig.canvas.draw()
                        fig.canvas.flush_events()

            except (ValueError, IndexError) as e:
                print(f"데이터 파싱 오류: {e}")
            except Exception as e:
                print(f"오류: {e}")
                break

except KeyboardInterrupt:
    print("\n🛑 서버를 종료합니다.")
finally:
    sock.close()
    print("소켓이 닫혔습니다.")