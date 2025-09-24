import socket
import matplotlib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from collections import deque
from matplotlib.animation import FuncAnimation
import csv
import datetime

matplotlib.use('TkAgg')

# ---------------------------
# 설정
# ---------------------------
HOST = '0.0.0.0'
PORT = 65000
WINDOW_SIZE = 20
STEP_SIZE = 10

# 최근 데이터 저장용 버퍼
buffer = deque(maxlen=WINDOW_SIZE + STEP_SIZE)
z_variances = []    # z_acc_variance 결과 저장
mean_pitches = []   # mean_pitch 결과 저장 (새로 추가)
new_data_counter = 0

# ---------------------------
# 특징 추출 함수 (z_acc_var와 mean_pitch 모두 계산)
# ---------------------------
def compute_feature(window_df):
    """WINDOW_SIZE 크기의 DataFrame을 받아 특징들을 계산합니다."""
    df = window_df.copy()
    
    # 이동 평균 적용 (ax, ay, az에 대해 적용)
    for col in ['ax', 'ay', 'az']:
        df[f'{col}_smooth'] = df[col].rolling(window=2).mean()
    df.dropna(inplace=True)
    
    if df.empty:
        return None, None # 두 개의 값을 반환하도록 수정

    # 1. z축 분산 계산 (계단, 단차용)
    z_acc_var = df['az_smooth'].var()

    # 2. 평균 기울기(pitch) 계산 (경사로용)
    # 중력 벡터 대비 현재 기기의 기울기 각도를 계산 (라디안)
    # atan2를 사용하여 피치 각도 계산 (더 직관적이고 안정적)
    # pitch = atan2(ax_smooth, sqrt(ay_smooth^2 + az_smooth^2))
    # 단, 센서 장착 방향에 따라 축이 바뀔 수 있음. 
    # 여기서는 "앞뒤 기울기"를 의미하는 ax, az 조합 사용.
    # 만약 Y축 기울기가 더 적절하면 atan2(ay_smooth, sqrt(ax_smooth^2 + az_smooth^2))로 변경

    # 현재 센서가 평지에 있을 때 az가 1g, ax,ay가 0g이라고 가정
    # x축(ax)이 앞뒤 기울기를 나타낸다고 가정하고 pitch 계산
    # (실제 센서 방향에 따라 ax, ay를 교체해야 할 수 있습니다)
    
    # 이전에 제안했던 arccos 방식
    norm = np.sqrt(df['ax_smooth']**2 + df['ay_smooth']**2 + df['az_smooth']**2)
    norm[norm == 0] = 1e-6 # 0으로 나누기 방지
    cos_theta = np.clip(df['az_smooth'] / norm, -1.0, 1.0)
    pitch_rad = np.mean(np.arccos(cos_theta)) # 평균적인 기울기
    
    # 혹은, 앞뒤 기울기를 직접적으로 나타내는 atan2 방식 (더 일반적)
    # atan2(y, x) -> atan2(가속도_앞뒤, sqrt(가속도_좌우^2 + 가속도_수직^2))
    # 센서가 앞으로 기울면 ax가 변하고, 옆으로 기울면 ay가 변함.
    # 여기서는 '앞뒤' 경사를 가정하고 ax를 사용.
    pitch_y_rad = np.mean(np.arctan2(df['ax_smooth'], np.sqrt(df['ay_smooth']**2 + df['az_smooth']**2)))
    # 절대값을 취하여 기울기 방향과 무관하게 '기울어진 정도'만 판단
    mean_pitch_absolute = np.abs(pitch_y_rad)
    
    return z_acc_var, mean_pitch_absolute # 계산된 두 특징을 반환

# ---------------------------
# 그래프 초기화 및 애니메이션 (2개의 서브플롯)
# ---------------------------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True) # x축 공유

# 첫 번째 서브플롯: Z-axis Variance
line1, = ax1.plot([], [], 'o-', label='Z-axis Variance')
ax1.set_title("Real-time Sensor Features")
ax1.set_ylabel("Z-axis Variance")
ax1.grid(True)
ax1.legend()
ax1.set_ylim(0, 0.1) # 초기 y축 범위

# 두 번째 서브플롯: Mean Pitch
line2, = ax2.plot([], [], 'o-', color='red', label='Mean Pitch (Absolute)')
ax2.set_xlabel("Feature Index")
ax2.set_ylabel("Mean Pitch (Radians)")
ax2.grid(True)
ax2.legend()
ax2.set_ylim(0, 0.5) # 초기 y축 범위

fig.tight_layout() # 그래프 간 간격 조정

def update(frame):
    # Z-axis Variance 그래프 업데이트
    if len(z_variances) > 0:
        xdata = list(range(len(z_variances)))
        ydata1 = z_variances
        line1.set_data(xdata, ydata1)
        ax1.set_xlim(0, max(50, len(z_variances) + 10))
        if ydata1:
            ax1.set_ylim(0, max(ydata1) * 1.2 + 0.01)
    
    # Mean Pitch 그래프 업데이트
    if len(mean_pitches) > 0:
        ydata2 = mean_pitches # xdata는 line1과 공유
        line2.set_data(xdata, ydata2)
        if ydata2:
            ax2.set_ylim(0, max(ydata2) * 1.2 + 0.01)
            
    return line1, line2 # 두 개의 Line2D 객체를 반환

ani = FuncAnimation(fig, update, interval=200, blit=True)

# ---------------------------
# TCP 서버 시작
# ---------------------------
print("Starting TCP Server...")
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    print(f"Server listening on {HOST}:{PORT}")
    print("Waiting for Arduino...")
    conn, addr = s.accept()
    print(f"Connected by {addr}")

    with conn:
        timestamp_start = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"sensor_log_{timestamp_start}.csv"
        print(f"Logging raw data to -> {filename}")

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # CSV 파일 헤더 작성 (timestamp 추가)
            header = ['lat','lon','ax','ay','az','gx','gy','gz','mx','my','mz', 'timestamp']
            writer.writerow(header)
            
            plt.show(block=False)
            fig.canvas.draw()
            fig.canvas.flush_events()

            while True:
                try:
                    raw_data = conn.recv(1024).decode('utf-8').strip()
                    if not raw_data:
                        print("Connection closed by client.")
                        break

                    for data_line in raw_data.split('\n'):
                        if not data_line: continue
                        
                        frame_values = list(map(float, data_line.split(',')))
                        if len(frame_values) != 11:
                            print(f"Skipping malformed data: {frame_values}")
                            continue
                        
                        # 현재 시간 추가
                        timestamp_now = datetime.datetime.now().isoformat()
                        full_frame = frame_values + [timestamp_now] # 원본 데이터 + 타임스탬프

                        # CSV 파일에 데이터 한 줄 쓰기
                        writer.writerow(full_frame)

                        # 버퍼에 데이터 추가 (원본 데이터만)
                        buffer.append(frame_values) # 버퍼에는 타임스탬프 제외한 원본 11개 값만 저장
                        new_data_counter += 1

                        if new_data_counter >= STEP_SIZE and len(buffer) >= WINDOW_SIZE:
                            new_data_counter = 0
                            
                            # 버퍼에서 WINDOW_SIZE만큼의 데이터프레임을 생성
                            window_data_for_df = list(buffer)[-WINDOW_SIZE:]
                            # DataFrame 생성 시에는 'timestamp' 컬럼을 제외한 원래의 11개 컬럼 이름만 사용
                            df = pd.DataFrame(window_data_for_df, columns=['lat','lon','ax','ay','az','gx','gy','gz','mx','my','mz'])
                            
                            z_var, pitch = compute_feature(df)
                            
                            if z_var is not None:
                                print(f"New Features -> z_variance: {z_var:.4f}, mean_pitch: {pitch:.4f}")
                                z_variances.append(z_var)
                                mean_pitches.append(pitch) # 새로운 리스트에 pitch 값 추가
                            
                            fig.canvas.draw()
                            fig.canvas.flush_events()

                except (ValueError, IndexError) as e:
                    print(f"Data parsing error: {e}")
                    continue
                except BrokenPipeError:
                    print("Connection lost.")
                    break
                except KeyboardInterrupt:
                    print("Server shutting down.")
                    break

print(f"Server has been shut down. Data saved in {filename}")