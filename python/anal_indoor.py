import pandas as pd
import numpy as np
import folium
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
from scipy.signal import find_peaks
import matplotlib.pyplot as plt

# ---------------------------
# 설정
# ---------------------------
# True: 실내 모드(PDR), False: 실외 모드(GPS)
IS_INDOOR_MODE = True

# 분석할 로그 파일 경로
INPUT_CSV_PATH = 'sensor_log_2025-09-25_01-13-54.csv' # 분석할 실제 파일명으로 변경하세요.

# 결과 저장 파일 경로
OUTPUT_ZONES_CSV_PATH = 'special_zones_output.csv'
OUTPUT_MAP_PATH_OUTDOOR = 'mobility_map_outdoor.html'
OUTPUT_MAP_PATH_INDOOR = 'indoor_path_estimation.png'

# 특징 추출 및 클러스터링 설정
WINDOW_SIZE = 20
STEP_SIZE = 10
MIN_POINTS_IN_CLUSTER = 3

# ▼▼▼ 지형 판단 임계값 (가슴 부착 기준) ▼▼▼
# 가슴은 평지에서 움직임이 적으므로, 발 부착 때보다 훨씬 낮은 값을 사용합니다.
VAR_THRESHOLD = 0.03   # z축 분산이 이 값 이상이면 '계단/단차'로 의심
PITCH_THRESHOLD = 0.2  # 평균 pitch가 이 값 이상이면 '경사로'로 의심

# ▼▼▼ 실내 PDR 튜닝 값 (가슴 부착 기준) ▼▼▼
SAMPLING_PERIOD = 0.02
# 가슴의 상하 움직임은 발의 충격보다 작으므로, prominence를 낮게 설정합니다.
PDR_PEAK_PROMINENCE = 0.15 
PDR_STEP_INTERVAL = int(0.4 / SAMPLING_PERIOD)
PDR_STEP_LENGTH = 0.65 

# ▼▼▼ 실외 칼만 필터 튜닝 값 ▼▼▼
KALMAN_R_VAL = 20; KALMAN_Q_VAL = 0.01
KOREA_BOUNDS = {'lat_min': 33.0, 'lat_max': 39.0, 'lon_min': 124.0, 'lon_max': 130.0}
ZONE_RADIUS = 5

# =================================================================================
# 실내 경로 추정 (PDR) 및 시각화 함수
# =================================================================================
def calculate_pdr_path(df):
    print("\n--- GPS 없이 실내 경로 추정(PDR)을 시작합니다 ---")
    pdr_df = df.copy()
    az_smooth = pdr_df['az'].rolling(window=5, center=True).mean().fillna(0)
    steps_indices, _ = find_peaks(az_smooth, prominence=PDR_PEAK_PROMINENCE, distance=PDR_STEP_INTERVAL)
    
    if len(steps_indices) < 2:
        print("경로를 추정하기에 걸음 수가 부족합니다. PDR_PEAK_PROMINENCE 값을 조절해보세요.")
        pdr_df['pos_x'] = 0; pdr_df['pos_y'] = 0
        return pdr_df

    print(f"PDR: 총 {len(steps_indices)}개의 걸음이 감지되었습니다.")

    gz_rad = np.deg2rad(pdr_df['gz'])
    heading = 0.0; pos_x = 0.0; pos_y = 0.0
    positions = np.zeros((len(pdr_df), 2))
    
    for i in range(1, len(steps_indices)):
        start_idx = steps_indices[i-1]
        end_idx = steps_indices[i]
        
        heading_change = gz_rad.iloc[start_idx:end_idx].sum() * SAMPLING_PERIOD
        heading += heading_change
        
        pos_x += PDR_STEP_LENGTH * np.cos(heading)
        pos_y += PDR_STEP_LENGTH * np.sin(heading)
        
        prev_pos_x = positions[start_idx-1, 0]
        prev_pos_y = positions[start_idx-1, 1]
        for j in range(start_idx, end_idx):
            ratio = (j - start_idx) / (end_idx - start_idx)
            positions[j, 0] = prev_pos_x + (pos_x - prev_pos_x) * ratio
            positions[j, 1] = prev_pos_y + (pos_y - prev_pos_y) * ratio
            
    positions[steps_indices[-1]:, :] = positions[steps_indices[-1]-1, :]
    pdr_df['pos_x'] = positions[:, 0]; pdr_df['pos_y'] = positions[:, 1]
    return pdr_df

def plot_indoor_path_matplotlib(pdr_df, zones_df):
    if pdr_df is None or pdr_df.empty:
        print("시각화할 경로 데이터가 없습니다."); return

    print(f"\n--- Matplotlib으로 실내 경로 및 특이 지점 시각화를 시작합니다 ---")
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.plot(pdr_df['pos_x'], pdr_df['pos_y'], color='lightblue', linewidth=3, label='Estimated Full Path', zorder=1)
    ax.scatter(pdr_df['pos_x'].iloc[0], pdr_df['pos_y'].iloc[0], c='green', s=150, label='Start', zorder=5, edgecolors='black')
    ax.scatter(pdr_df['pos_x'].iloc[-1], pdr_df['pos_y'].iloc[-1], c='black', s=200, marker='X', label='End', zorder=5)

    if zones_df is not None and not zones_df.empty:
        stair_zones = zones_df[zones_df['type'].str.contains('Stair')]
        ramp_zones = zones_df[zones_df['type'].str.contains('Ramp')]
        ax.scatter(stair_zones['pos_x'], stair_zones['pos_y'], c='red', s=100, marker='^', label='Stair/Bump Zones', zorder=10, edgecolors='black')
        ax.scatter(ramp_zones['pos_x'], ramp_zones['pos_y'], c='orange', s=120, marker='s', label='Ramp Zones', zorder=10, edgecolors='black')

    ax.set_title('Indoor Path Estimation (PDR) with Special Zones', fontsize=16)
    ax.set_xlabel('X Position (m)'); ax.set_ylabel('Y Position (m)')
    ax.set_aspect('equal', adjustable='box'); ax.legend(); ax.grid(True)
    plt.savefig(OUTPUT_MAP_PATH_INDOOR); print(f"실내 경로 지도를 '{OUTPUT_MAP_PATH_INDOOR}' 파일로 저장했습니다."); plt.show()

# =================================================================================
# 실외 경로 추정 (GPS) 및 공통 분석 함수
# =================================================================================
def apply_kalman_filter(df):
    kf_lat = KalmanFilter(dim_x=2, dim_z=1)
    kf_lat.F = np.array([[1., 1.], [0., 1.]]); kf_lat.H = np.array([[1., 0.]]); kf_lat.R = KALMAN_R_VAL
    kf_lat.Q = Q_discrete_white_noise(dim=2, dt=1., var=KALMAN_Q_VAL); kf_lat.x = np.array([[df['lat'].iloc[0]], [0.]])
    kf_lon = KalmanFilter(dim_x=2, dim_z=1)
    kf_lon.F = np.array([[1., 1.], [0., 1.]]); kf_lon.H = np.array([[1., 0.]]); kf_lon.R = KALMAN_R_VAL
    kf_lon.Q = Q_discrete_white_noise(dim=2, dt=1., var=KALMAN_Q_VAL); kf_lon.x = np.array([[df['lon'].iloc[0]], [0.]])
    lat_filtered, lon_filtered = [], []
    for _, row in df.iterrows():
        kf_lat.predict(); kf_lat.update(row['lat']); lat_filtered.append(kf_lat.x[0, 0])
        kf_lon.predict(); kf_lon.update(row['lon']); lon_filtered.append(kf_lon.x[0, 0])
    df['lat_filtered'] = lat_filtered; df['lon_filtered'] = lon_filtered
    print("칼만 필터 적용 완료."); return df

# ---------------------------
# 1. CSV 파일 로드 및 특징 추출 (수정된 최종 버전)
# ---------------------------
def analyze_log_file(filepath, is_indoor=False):
    """
    CSV 파일을 로드하고 분석합니다. is_indoor 플래그에 따라 GPS 처리 또는 PDR을 수행합니다.
    """
    print(f"'{filepath}' 파일을 분석합니다...")
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다. -> {filepath}"); return None, None
    
    if is_indoor:
        # 실내 모드: PDR 경로 계산
        pdr_df = calculate_pdr_path(df)
        
        # ▼▼▼ 여기가 핵심 수정 부분입니다 ▼▼▼
        # 특징 추출에 필요한 컬럼만 명시적으로 선택합니다.
        # 이렇게 하면 timestamp 등 다른 타입의 데이터가 섞이는 것을 원천적으로 방지합니다.
        imu_cols = ['ax', 'ay', 'az', 'gx', 'gy', 'gz', 'mx', 'my', 'mz']
        pdr_cols = ['pos_x', 'pos_y']
        
        # 필요한 컬럼만으로 새로운 데이터프레임을 생성
        feature_coord_df = pdr_df[imu_cols + pdr_cols].copy()
        
        # PDR 좌표를 특징 추출 함수가 이해할 수 있도록 lat, lon으로 이름 변경
        feature_coord_df.rename(columns={'pos_x': 'lat', 'pos_y': 'lon'}, inplace=True)
        # ▲▲▲ 수정 완료 ▲▲▲

        processed_df = pdr_df # 시각화를 위한 전체 데이터는 그대로 유지

    else:
        # 실외 모드 (기존 로직과 동일)
        df.dropna(subset=['lat', 'lon'], inplace=True)
        df = df[(df['lat'] != 0) & (df['lon'] != 0)]
        df = df[(df['lat'] >= KOREA_BOUNDS['lat_min']) & (df['lat'] <= KOREA_BOUNDS['lat_max']) &
                (df['lon'] >= KOREA_BOUNDS['lon_min']) & (df['lon'] <= KOREA_BOUNDS['lon_max'])].reset_index(drop=True)
        if df.empty: print("오류: 유효한 GPS 데이터가 없습니다."); return None, None
        processed_df = apply_kalman_filter(df.copy())
        feature_coord_df = processed_df.rename(columns={'lat_filtered': 'lat', 'lon_filtered': 'lon'})
    
    # 공통 특징 추출 로직 (수정 없음)
    features_list = []
    for i in range(0, len(feature_coord_df) - WINDOW_SIZE, STEP_SIZE):
        window = feature_coord_df.iloc[i:i + WINDOW_SIZE].copy()
        for col in ['ax', 'ay', 'az']: window[f'{col}_smooth'] = window[col].rolling(window=2).mean()
        window.dropna(inplace=True)
        if window.empty: continue
        z_acc_var = window[f'az_smooth'].var()
        pitch_y_rad = np.mean(np.arctan2(window['ax_smooth'], np.sqrt(window['ay_smooth']**2 + window['az_smooth']**2)))
        mean_pitch_absolute = np.abs(pitch_y_rad)
        features_list.append({'z_variance': z_acc_var, 'mean_pitch': mean_pitch_absolute,
                              'lat': window['lat'].median(), 'lon': window['lon'].median()})

    return pd.DataFrame(features_list), processed_df

def process_and_cluster_zones(feature_df):
    if feature_df is None or feature_df.empty: return None
    # 가슴 부착 센서에 맞는 단순 임계값 기반 로직
    feature_df['is_stair'] = feature_df['z_variance'] > VAR_THRESHOLD
    feature_df['is_ramp'] = feature_df['mean_pitch'] > PITCH_THRESHOLD
    
    feature_df['stair_cluster_id'] = (feature_df['is_stair'].diff() != 0).cumsum()
    feature_df['ramp_cluster_id'] = (feature_df['is_ramp'].diff() != 0).cumsum()

    zone_summary_list = []
    stair_clusters = feature_df[feature_df['is_stair']].groupby('stair_cluster_id')
    for _, cluster_df in stair_clusters:
        if len(cluster_df) >= MIN_POINTS_IN_CLUSTER:
            zone_summary_list.append({'type': 'Stair/Bump Zone', 'lat': cluster_df['lat'].mean(), 'lon': cluster_df['lon'].mean()})
            
    ramp_clusters = feature_df[feature_df['is_ramp']].groupby('ramp_cluster_id')
    for _, cluster_df in ramp_clusters:
        if len(cluster_df) >= MIN_POINTS_IN_CLUSTER:
            if not (feature_df.loc[cluster_df.index]['is_stair']).any():
                 zone_summary_list.append({'type': 'Ramp Zone', 'lat': cluster_df['lat'].mean(), 'lon': cluster_df['lon'].mean()})

    if not zone_summary_list:
        print("분석 결과, 기준을 만족하는 특이 구역(Zone)이 발견되지 않았습니다."); return None
        
    zones_df = pd.DataFrame(zone_summary_list)
    print(f"\n총 {len(zones_df)}개의 특이 구역(Zone)을 발견했습니다."); print(zones_df)
    zones_df.to_csv(OUTPUT_ZONES_CSV_PATH, index=False)
    print(f"특이 구역 정보를 '{OUTPUT_ZONES_CSV_PATH}' 파일에 저장했습니다.")
    return zones_df

def create_map_with_zones(zones_df, original_df):
    if (zones_df is None or zones_df.empty) and (original_df is None or original_df.empty):
        print("지도에 표시할 데이터가 없습니다."); return
        
    map_center = [original_df['lat_filtered'].iloc[0], original_df['lon_filtered'].iloc[0]] if not original_df.empty else [zones_df['lat'].iloc[0], zones_df['lon'].iloc[0]]
    m = folium.Map(location=map_center, zoom_start=18)

    if not original_df.empty:
        points_raw = original_df[['lat', 'lon']].values.tolist()
        folium.PolyLine(points_raw, color='gray', weight=2.5, opacity=0.8, popup='Raw GPS Path').add_to(m)
        points_filtered = original_df[['lat_filtered', 'lon_filtered']].values.tolist()
        folium.PolyLine(points_filtered, color='blue', weight=5, opacity=0.8, popup='Kalman Filtered Path').add_to(m)

    if zones_df is not None and not zones_df.empty:
        for idx, row in zones_df.iterrows():
            color = 'red' if 'Stair' in row['type'] else 'orange'
            folium.Circle(location=[row['lat'], row['lon']], radius=ZONE_RADIUS, color=color, fill=True, fill_color=color, fill_opacity=0.3, popup=row['type']).add_to(m)

    m.save(OUTPUT_MAP_PATH_OUTDOOR); print(f"\n지도를 '{OUTPUT_MAP_PATH_OUTDOOR}' 파일에 저장했습니다.")

# =================================================================================
# 메인 코드 실행
# =================================================================================
if __name__ == "__main__":
    
    if IS_INDOOR_MODE:
        print("====== [실내 모드]로 분석을 시작합니다. ======")
        features, pdr_data_with_path = analyze_log_file(INPUT_CSV_PATH, is_indoor=True)

        if pdr_data_with_path is not None:
            zones = process_and_cluster_zones(features)
            if zones is not None:
                zones.rename(columns={'lat': 'pos_x', 'lon': 'pos_y'}, inplace=True)
            plot_indoor_path_matplotlib(pdr_data_with_path, zones)
    else:
        print("====== [실외 모드]로 분석을 시작합니다. ======")
        features, original_data_with_filter = analyze_log_file(INPUT_CSV_PATH, is_indoor=False)
        
        if original_data_with_filter is not None:
            zones = process_and_cluster_zones(features)
            create_map_with_zones(zones, original_data_with_filter)