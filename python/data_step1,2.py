import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import os

    # 2단계에서 생성된 feature_df를 사용합니다.
import matplotlib.pyplot as plt

# --- 코드 실행 전 설정 ---
# 가지고 계신 실제 데이터 파일 경로를 지정해주세요.
# 예: FILE_PATH = 'C:/Users/MyUser/Documents/my_real_data.csv'
FILE_PATH = 'sensor_log_2025-09-26_03-40-56.csv'

# --- 예제 데이터 생성 (수정됨) ---
def create_dummy_data(filename):
    """테스트를 위한 가상 센서 데이터 CSV 파일을 생성합니다. (컬럼 순서 변경)"""
    if os.path.exists(filename):
        print(f"'{filename}' 파일이 이미 존재하여 새로 생성하지 않습니다.")
        return
        
    print(f"'{filename}' 예제 파일을 생성합니다...")
    num_points = 500
    
    # 기본 노이즈 생성
    noise = lambda: np.random.normal(0, 0.05, num_points)
    
    # 각 축 데이터 초기화
    ax, ay, az = noise(), noise(), np.ones(num_points) + noise() # 평지 (Z축에 중력가속도)
    gx, gy, gz = noise(), noise(), noise()
    mx, my, mz = noise(), noise(), noise()
    
    # 구간별 특징 데이터 삽입
    # 1. 경사로 (100-200 구간)
    ay[100:200] += 0.3 # 앞으로 기울어짐
    az[100:200] -= 0.3
    
    # 2. 계단 (300-400 구간)
    for i in range(300, 400, 10): # 10개 데이터마다 충격 발생
        az[i:i+3] += 1.5 # 강한 수직 충격
        
    # 3. 단차 (450 구간)
    az[450:454] += 2.5 # 한번의 매우 강한 충격

    # GPS 좌표 (서울 시내를 따라 이동하는 것처럼 시뮬레이션)
    lat = np.linspace(37.5665, 37.5700, num_points)
    lon = np.linspace(126.9780, 126.9820, num_points)
    
    dummy_df = pd.DataFrame({
        'lat': lat, 'lon': lon, # <--- 컬럼 순서 변경
        'ax': ax, 'ay': ay, 'az': az,
        'gx': gx, 'gy': gy, 'gz': gz, 
        'mx': mx, 'my': my, 'mz': mz
    })
    dummy_df.to_csv(filename, index=False, header=False)

# --------------------------------------------------------------------
# 🚀 1단계: 데이터 로딩 및 전처리 (수정됨)
# --------------------------------------------------------------------
def load_and_preprocess_data(filepath):
    """
    CSV 파일을 로드하고 기본적인 전처리를 수행합니다.
    """
    print("\n--- 1단계: 데이터 로딩 및 전처리 시작 ---")
    
    # CSV 파일 읽기 (컬럼 순서 변경)
    col_names = ['lat', 'lon', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'mx', 'my', 'mz', 'timestamp']
    df = pd.read_csv(filepath, names=col_names, skiprows=1)
    
    # 결측치가 있는 행 제거
    df.dropna(inplace=True)
    
    # 이동 평균 필터 적용
    window_size = 3
    for col in ['ax', 'ay', 'az', 'gx', 'gy', 'gz']:
        df[f'{col}_smooth'] = df[col].rolling(window=window_size).mean()
        
    # 이동 평균 계산 후 생긴 결측치 다시 제거
    df.dropna(inplace=True)
    
    print("전처리 완료! 데이터 샘플:")
    print(df.head(100))
    return df

# --------------------------------------------------------------------
# 💡 2단계: 특징 추출 (Feature Engineering) (수정됨)
# --------------------------------------------------------------------
def extract_features(df, window_size, step_size):
    """
    전처리된 데이터에서 슬라이딩 윈도우를 이용해 특징을 추출합니다.
    """
    print("\n--- 2단계: 특징 추출 시작 ---")
    
    features_list = []
    
    for i in range(0, len(df) - window_size, step_size):
        window = df.iloc[i : i + window_size]
        
        # --- 특징 계산 ---
        z_acc_var = window['az_smooth'].var()
        y_acc_mean = window['ay_smooth'].mean()
        
        norm = np.sqrt(window['ax_smooth']**2 + window['ay_smooth']**2 + window['az_smooth']**2)
        norm[norm == 0] = 1e-6
        cos_theta = np.clip(window['az_smooth'] / norm, -1.0, 1.0)
        pitch_rad = np.arccos(cos_theta)
        mean_pitch = np.mean(pitch_rad)

        # extract_features 함수 내부의 find_peaks 라인을 수정합니다.
        # 최소 0.3 이상의 높이를 가지며, 최소 15 데이터 포인트 이상 떨어진 피크만 찾기
        peaks, _ = find_peaks(window['az_smooth'], height=0.3)
        num_peaks = len(peaks)

        # extract_features 함수 내부의 특징 계산 부분에 추가합니다.
        z_acc_range = window['az_smooth'].max() - window['az_smooth'].min()
        
        # --- 결과 저장 ---
        features = {
            'window_index': i,            # <--- 'start_time' 대신 윈도우 시작 인덱스 저장
            'z_acc_variance': z_acc_var,
            'y_acc_mean': y_acc_mean,
            'z_acc_range': z_acc_range,
            'mean_pitch': mean_pitch,
            'num_peaks': num_peaks,
            'lat': window['lat'].median(),
            'lon': window['lon'].median()
        }
        features_list.append(features)
        
    feature_df = pd.DataFrame(features_list)
    print("특징 추출 완료! 추출된 특징 샘플:")
    print(feature_df.head())
    return feature_df

# --------------------------------------------------------------------
# 메인 코드 실행
# --------------------------------------------------------------------
if __name__ == "__main__":
    # 0단계: 테스트용 더미 데이터 생성
    # create_dummy_data(FILE_PATH)
    
    # 1단계 실행
    preprocessed_df = load_and_preprocess_data(FILE_PATH)
    
    # 2단계 실행
    feature_df = extract_features(preprocessed_df, window_size=10, step_size=5)

    print("\n\n✅ 모든 단계가 성공적으로 실행되었습니다.")
    print(f"총 {len(feature_df)}개의 특징 세트가 생성되었습니다.")


    feature_df['z_acc_variance'].plot(figsize=(15, 5), marker='o')
    plt.title('Z-axis Variance over Time (All Windows)')
    plt.xlabel('Window Sequence')
    plt.ylabel('Variance')
    plt.grid(True)
    plt.show()