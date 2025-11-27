import pandas as pd
import numpy as np
import folium
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise
from scipy.signal import find_peaks

# ---------------------------
# 설정
# ---------------------------
INPUT_CSV_PATH = 'sensor_log_2025-09-26_06-17-39.csv' # 실제 파일명으로 변경하세요.
OUTPUT_ZONES_CSV_PATH = 'special_zones_kalman.csv'
OUTPUT_MAP_PATH = 'mobility_map_kalman.html'

WINDOW_SIZE = 10
STEP_SIZE = 5

VAR_THRESHOLD = 0.03
PITCH_THRESHOLD = 0.4
MIN_POINTS_IN_CLUSTER = 3
ZONE_RADIUS = 20

# ▼▼▼ 칼만 필터 튜닝 설정값 ▼▼▼
# R: 측정 노이즈(GPS 오차). 값이 클수록 GPS를 덜 신뢰함. GPS가 많이 튀면 값을 키워보세요.
KALMAN_R_VAL = 20
# Q: 프로세스 노이즈(움직임의 불확실성). 값이 클수록 움직임이 급변한다고 가정함.
KALMAN_Q_VAL = 0.01

# ▼▼▼ 유효 GPS 좌표 범위 설정 추가 ▼▼▼
# 한반도 근처의 대략적인 위경도 경계 (Bounding Box)
KOREA_BOUNDS = {
    'lat_min': 33.0,
    'lat_max': 39.0,
    'lon_min': 124.0,
    'lon_max': 130.0
}

# ▼▼▼ 보행 분석(Gait Analysis) 튜닝 설정값 ▼▼▼
# ZUPT를 감지할 자이로스코프의 각속도 변화량 임계값 (deg/s). 작을수록 민감.
ZUPT_GYRO_THRESHOLD = 150
# 데이터 샘플링 주기 (초 단위). 아두이노 코드의 delay와 관련. 50Hz -> 0.02초
SAMPLING_PERIOD = 0.02

# ▼▼▼ 동적 반지름(Dynamic Radius)을 위한 설정값 추가 ▼▼▼
# points_count에 곱해질 값. 클수록 원이 더 빨리 커집니다.
RADIUS_SCALING_FACTOR = 2
# 아무리 작은 클러스터라도 지도에 표시될 최소 반지름 (미터)
MIN_RADIUS = 3 
# ▲▲▲ 여기까지 추가 ▲▲▲

# ---------------------------
# 0. 칼만 필터 적용 함수 (새로 추가)
# ---------------------------
# ---------------------------
# 0. 칼만 필터 적용 함수 (수정된 버전)
# ---------------------------
def apply_kalman_filter(df):
    """DataFrame에 있는 lat, lon 데이터에 칼만 필터를 적용하여 경로를 보정합니다."""
    
    # ------------------ ▼▼▼ 수정된 부분 ▼▼▼ ------------------

    # 1. 위도(Latitude)용 칼만 필터 설정
    kf_lat = KalmanFilter(dim_x=2, dim_z=1)
    kf_lat.F = np.array([[1., 1.], [0., 1.]])      # 상태 전이 행렬
    kf_lat.H = np.array([[1., 0.]])      # 측정 함수
    kf_lat.R = KALMAN_R_VAL             # 측정 노이즈
    kf_lat.Q = Q_discrete_white_noise(dim=2, dt=1., var=KALMAN_Q_VAL) # 프로세스 노이즈
    kf_lat.x = np.array([[df['lat'].iloc[0]], [0.]]) # 초기 상태

    # 2. 경도(Longitude)용 칼만 필터 설정 (별도로!)
    kf_lon = KalmanFilter(dim_x=2, dim_z=1)
    kf_lon.F = np.array([[1., 1.], [0., 1.]])
    kf_lon.H = np.array([[1., 0.]])
    kf_lon.R = KALMAN_R_VAL
    kf_lon.Q = Q_discrete_white_noise(dim=2, dt=1., var=KALMAN_Q_VAL)
    kf_lon.x = np.array([[df['lon'].iloc[0]], [0.]])
    
    # ------------------ ▲▲▲ 수정 완료 ▲▲▲ ------------------

    # 필터링 실행 (이 부분은 동일)
    lat_filtered, lon_filtered = [], []
    for _, row in df.iterrows():
        kf_lat.predict()
        kf_lat.update(row['lat'])
        lat_filtered.append(kf_lat.x[0, 0])

        kf_lon.predict()
        kf_lon.update(row['lon'])
        lon_filtered.append(kf_lon.x[0, 0])
        
    df['lat_filtered'] = lat_filtered
    df['lon_filtered'] = lon_filtered
    print("칼만 필터 적용 완료. GPS 경로가 보정되었습니다.")
    return df

# ---------------------------
# 1. CSV 파일 로드 및 특징 추출 (수정됨)
# ---------------------------
# ---------------------------
# 1. CSV 파일 로드 및 특징 추출 (수정된 버전)
# ---------------------------
def analyze_log_file(filepath):
    print(f"'{filepath}' 파일을 분석합니다...")
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다. -> {filepath}")
        return None, None

    # ▼▼▼ 데이터 유효성 검사 로직 추가 ▼▼▼
    
    # 0,0 좌표 및 null 값 제거
    original_rows = len(df)
    df.dropna(subset=['lat', 'lon'], inplace=True)
    df = df[(df['lat'] != 0) & (df['lon'] != 0)]
    
    # 지리적 경계(Bounding Box) 필터링
    df = df[
        (df['lat'] >= KOREA_BOUNDS['lat_min']) &
        (df['lat'] <= KOREA_BOUNDS['lat_max']) &
        (df['lon'] >= KOREA_BOUNDS['lon_min']) &
        (df['lon'] <= KOREA_BOUNDS['lon_max'])
    ].reset_index(drop=True)

    filtered_rows = len(df)
    removed_count = original_rows - filtered_rows
    if removed_count > 0:
        print(f"비정상 GPS 좌표 데이터 {removed_count}개를 제거했습니다.")

    # ▲▲▲ 여기까지 추가 ▲▲▲

    if df.empty:
        print("오류: 유효한 GPS 데이터가 남아있지 않습니다.")
        return None, None

    # 칼만 필터 적용 단계
    df_kalman = apply_kalman_filter(df.copy())
    
    features_list = []
    for i in range(0, len(df_kalman) - WINDOW_SIZE, STEP_SIZE):
        window = df_kalman.iloc[i:i + WINDOW_SIZE].copy()
        
        for col in ['ax', 'ay', 'az']:
            window[f'{col}_smooth'] = window[col].rolling(window=2).mean()
        window.dropna(inplace=True)
        if window.empty: continue
        z_acc_var = window['az_smooth'].var()
        pitch_y_rad = np.mean(np.arctan2(window['ax_smooth'], np.sqrt(window['ay_smooth']**2 + window['az_smooth']**2)))
        mean_pitch_absolute = np.abs(pitch_y_rad)
        
        features_list.append({
            'z_variance': z_acc_var, 'mean_pitch': mean_pitch_absolute,
            'lat': window['lat_filtered'].median(),
            'lon': window['lon_filtered'].median()
        })
        
    return pd.DataFrame(features_list), df_kalman

# ---------------------------
# 2. 특이 지점 클러스터링 (이전과 동일)
# ---------------------------
def process_and_cluster_zones(feature_df):
    if feature_df is None: return None
    # (이전 답변과 동일한 클러스터링 로직)
    feature_df['is_stair'] = feature_df['z_variance'] > VAR_THRESHOLD
    feature_df['is_ramp'] = feature_df['mean_pitch'] > PITCH_THRESHOLD
    feature_df['stair_cluster_id'] = (feature_df['is_stair'].diff() != 0).cumsum()
    feature_df['ramp_cluster_id'] = (feature_df['is_ramp'].diff() != 0).cumsum()
    zone_summary_list = []
    stair_clusters = feature_df[feature_df['is_stair']].groupby('stair_cluster_id')
    for _, cluster_df in stair_clusters:
        if len(cluster_df) >= MIN_POINTS_IN_CLUSTER:
            zone_summary_list.append({
                'type': 'Stair/Bump Zone', 'lat': cluster_df['lat'].mean(), 'lon': cluster_df['lon'].mean(),
                'points_count': len(cluster_df), 'max_variance': cluster_df['z_variance'].max(), 'avg_pitch': cluster_df['mean_pitch'].mean()
            })
    ramp_clusters = feature_df[feature_df['is_ramp']].groupby('ramp_cluster_id')
    for _, cluster_df in ramp_clusters:
        if len(cluster_df) >= MIN_POINTS_IN_CLUSTER:
            is_already_processed_as_stair = ((cluster_df['z_variance'] > VAR_THRESHOLD).any() and (cluster_df['z_variance'].mean() > VAR_THRESHOLD))
            if not is_already_processed_as_stair:
                 zone_summary_list.append({
                    'type': 'Ramp Zone', 'lat': cluster_df['lat'].mean(), 'lon': cluster_df['lon'].mean(),
                    'points_count': len(cluster_df), 'max_variance': cluster_df['z_variance'].max(), 'avg_pitch': cluster_df['mean_pitch'].mean()
                })
    if not zone_summary_list:
        print("분석 결과, 기준을 만족하는 특이 구역(Zone)이 발견되지 않았습니다.")
        return None
    zones_df = pd.DataFrame(zone_summary_list)
    zones_df.to_csv(OUTPUT_ZONES_CSV_PATH, index=False)
    print(f"\n총 {len(zones_df)}개의 특이 구역(Zone)을 발견했습니다.\n{zones_df}")
    return zones_df

# ---------------------------
# 3. Folium으로 지도 시각화 (수정됨)
# ---------------------------
def create_map_with_zones(zones_df, original_df):
    if zones_df is None or zones_df.empty:
        print("지도에 표시할 구역이 없어 시각화를 건너뜁니다.")
        return

    map_center = [zones_df['lat'].iloc[0], zones_df['lon'].iloc[0]]
    m = folium.Map(location=map_center, zoom_start=18)

    # ▼▼▼ 경로 표시 기능 추가 ▼▼▼
    # 1. 원본 GPS 경로 (회색 실선)
    points_raw = original_df[['lat', 'lon']].values.tolist()
    folium.PolyLine(points_raw, color='gray', weight=2.5, opacity=0.8, popup='Raw GPS Path').add_to(m)
    
    # 2. 칼만 필터 보정 경로 (파란색 굵은 선)
    points_filtered = original_df[['lat_filtered', 'lon_filtered']].values.tolist()
    folium.PolyLine(points_filtered, color='blue', weight=5, opacity=0.8, popup='Kalman Filtered Path').add_to(m)

    # (이전과 동일한 존 시각화 로직)
    for idx, row in zones_df.iterrows():
        zone_type = row['type']
        color = 'red' if 'Stair' in zone_type else 'orange'
        popup_html = f"""<b>Type:</b> {zone_type}<br><b>Points Count:</b> {row['points_count']}"""
        folium.Circle(
            location=[row['lat'], row['lon']], radius=ZONE_RADIUS, color=color,
            fill=True, fill_color=color, fill_opacity=0.3, popup=folium.Popup(popup_html, max_width=250)
        ).add_to(m)

    m.save(OUTPUT_MAP_PATH)
    print(f"\n구역 지도를 '{OUTPUT_MAP_PATH}' 파일에 성공적으로 저장했습니다.")

def apply_kalman_filter(df):
    kf_lat = KalmanFilter(dim_x=2, dim_z=1)
    kf_lat.F = np.array([[1., 1.], [0., 1.]]); kf_lat.H = np.array([[1., 0.]])
    kf_lat.R = KALMAN_R_VAL; kf_lat.Q = Q_discrete_white_noise(dim=2, dt=1., var=KALMAN_Q_VAL)
    kf_lat.x = np.array([[df['lat'].iloc[0]], [0.]])
    kf_lon = KalmanFilter(dim_x=2, dim_z=1)
    kf_lon.F = np.array([[1., 1.], [0., 1.]]); kf_lon.H = np.array([[1., 0.]])
    kf_lon.R = KALMAN_R_VAL; kf_lon.Q = Q_discrete_white_noise(dim=2, dt=1., var=KALMAN_Q_VAL)
    kf_lon.x = np.array([[df['lon'].iloc[0]], [0.]])
    lat_filtered, lon_filtered = [], []
    for _, row in df.iterrows():
        kf_lat.predict(); kf_lat.update(row['lat']); lat_filtered.append(kf_lat.x[0, 0])
        kf_lon.predict(); kf_lon.update(row['lon']); lon_filtered.append(kf_lon.x[0, 0])
    df['lat_filtered'] = lat_filtered; df['lon_filtered'] = lon_filtered
    print("칼만 필터 적용 완료. GPS 경로가 보정되었습니다.")
    return df

def analyze_log_file(filepath):
    print(f"'{filepath}' 파일을 분석합니다...")
    try:
        df = pd.read_csv(filepath)
        original_rows = len(df)
        df.dropna(subset=['lat', 'lon'], inplace=True)
        df = df[(df['lat'] != 0) & (df['lon'] != 0)]
        df = df[(df['lat'] >= KOREA_BOUNDS['lat_min']) & (df['lat'] <= KOREA_BOUNDS['lat_max']) &
                (df['lon'] >= KOREA_BOUNDS['lon_min']) & (df['lon'] <= KOREA_BOUNDS['lon_max'])].reset_index(drop=True)
        removed_count = original_rows - len(df)
        if removed_count > 0: print(f"비정상 GPS 좌표 데이터 {removed_count}개를 제거했습니다.")
        if df.empty: print("오류: 유효한 GPS 데이터가 없습니다."); return None, None
    except FileNotFoundError: print(f"오류: 파일을 찾을 수 없습니다. -> {filepath}"); return None, None
    df_kalman = apply_kalman_filter(df.copy())
    features_list = []
    for i in range(0, len(df_kalman) - WINDOW_SIZE, STEP_SIZE):
        window = df_kalman.iloc[i:i + WINDOW_SIZE].copy()
        for col in ['ax', 'ay', 'az']: window[f'{col}_smooth'] = window[col].rolling(window=2).mean()
        window.dropna(inplace=True)
        if window.empty: continue
        z_acc_var = window['az_smooth'].var()
        pitch_y_rad = np.mean(np.arctan2(window['ax_smooth'], np.sqrt(window['ay_smooth']**2 + window['az_smooth']**2)))
        mean_pitch_absolute = np.abs(pitch_y_rad)
        features_list.append({'z_variance': z_acc_var, 'mean_pitch': mean_pitch_absolute,
                              'lat': window['lat_filtered'].median(), 'lon': window['lon_filtered'].median()})
    return pd.DataFrame(features_list), df_kalman

def process_and_cluster_zones(feature_df):
    if feature_df is None: return None
    feature_df['is_stair'] = feature_df['z_variance'] > VAR_THRESHOLD
    feature_df['is_ramp'] = feature_df['mean_pitch'] > PITCH_THRESHOLD
    feature_df['stair_cluster_id'] = (feature_df['is_stair'].diff() != 0).cumsum()
    feature_df['ramp_cluster_id'] = (feature_df['is_ramp'].diff() != 0).cumsum()
    zone_summary_list = []
    stair_clusters = feature_df[feature_df['is_stair']].groupby('stair_cluster_id')
    for _, cluster_df in stair_clusters:
        if len(cluster_df) >= MIN_POINTS_IN_CLUSTER:
            zone_summary_list.append({'type': 'Stair/Bump Zone', 'lat': cluster_df['lat'].mean(), 'lon': cluster_df['lon'].mean(),
                                       'points_count': len(cluster_df), 'max_variance': cluster_df['z_variance'].max(), 'avg_pitch': cluster_df['mean_pitch'].mean()})
    ramp_clusters = feature_df[feature_df['is_ramp']].groupby('ramp_cluster_id')
    for _, cluster_df in ramp_clusters:
        if len(cluster_df) >= MIN_POINTS_IN_CLUSTER:
            is_already_processed_as_stair = ((cluster_df['z_variance'] > VAR_THRESHOLD).any() and (cluster_df['z_variance'].mean() > VAR_THRESHOLD))
            if not is_already_processed_as_stair:
                 zone_summary_list.append({'type': 'Ramp Zone', 'lat': cluster_df['lat'].mean(), 'lon': cluster_df['lon'].mean(),
                                            'points_count': len(cluster_df), 'max_variance': cluster_df['z_variance'].max(), 'avg_pitch': cluster_df['mean_pitch'].mean()})
    if not zone_summary_list: print("분석 결과, 기준을 만족하는 특이 구역(Zone)이 발견되지 않았습니다."); return None
    zones_df = pd.DataFrame(zone_summary_list)
    zones_df.to_csv(OUTPUT_ZONES_CSV_PATH, index=False)
    print(f"\n총 {len(zones_df)}개의 특이 구역(Zone)을 발견했습니다.\n{zones_df}")
    return zones_df

# ---------------------------
# 3. Folium으로 지도 시각화 (수정된 버전)
# ---------------------------
def create_map_with_zones(zones_df, original_df):
    if zones_df is None or zones_df.empty: 
        print("지도에 표시할 구역이 없어 시각화를 건너뜁니다.")
        # 특이 지점이 없더라도 경로는 표시할 수 있도록 수정
        if original_df is None or original_df.empty:
            return
        else:
            map_center = [original_df['lat_filtered'].iloc[0], original_df['lon_filtered'].iloc[0]]
    else:
        map_center = [zones_df['lat'].iloc[0], zones_df['lon'].iloc[0]]
        
    m = folium.Map(location=map_center, zoom_start=18)

    # 경로 표시 기능 (원본 GPS + 칼만 필터)
    if original_df is not None and not original_df.empty:
        points_raw = original_df[['lat', 'lon']].values.tolist()
        folium.PolyLine(points_raw, color='gray', weight=2.5, opacity=0.8, popup='Raw GPS Path').add_to(m)
        points_filtered = original_df[['lat_filtered', 'lon_filtered']].values.tolist()
        folium.PolyLine(points_filtered, color='blue', weight=5, opacity=0.8, popup='Kalman Filtered Path').add_to(m)

    # ▼▼▼ 여기가 핵심 수정 부분 ▼▼▼
    # 특이 지점(Zone) 시각화 로직
    if zones_df is not None and not zones_df.empty:
        for idx, row in zones_df.iterrows():
            zone_type = row['type']
            color = 'red' if 'Stair' in zone_type else 'orange'
            
            # 동적 반지름 계산
            # max()를 사용하여 최소 반지름보다 작아지지 않도록 보장
            dynamic_radius = max(MIN_RADIUS, row['points_count'] * RADIUS_SCALING_FACTOR)
            
            popup_html = f"""
            <b>Type:</b> {zone_type}<br>
            <b>Points Count:</b> {row['points_count']}<br>
            <b>Calculated Radius:</b> {dynamic_radius:.1f} m
            """
            
            folium.Circle(
                location=[row['lat'], row['lon']], 
                radius=dynamic_radius, # 고정값 대신 동적 반지름 사용
                color=color,
                fill=True, 
                fill_color=color, 
                fill_opacity=0.4, 
                popup=folium.Popup(popup_html, max_width=250)
            ).add_to(m)
    # ▲▲▲ 수정 완료 ▲▲▲

    m.save(OUTPUT_MAP_PATH)
    print(f"\n구역 지도를 '{OUTPUT_MAP_PATH}' 파일에 성공적으로 저장했습니다.")

# ---------------------------
# 4. 보행 분석 함수 (수정된 최종 버전)
# ---------------------------
def detect_steps_and_gait_features(df):
    """
    자이로스코프 데이터를 이용해 ZUPT를 감지하고,
    이를 바탕으로 걸음(step)을 분리하여 케이던스와 GCT를 계산합니다.
    """
    print("\n--- 보행 안정성 분석 시작 ---")
    
    # 자이로 데이터 스무딩
    df_gait = df.copy()
    for col in ['gx', 'gy', 'gz']:
        df_gait[col] = df_gait[col].rolling(window=5, center=True).mean()
    df_gait.dropna(inplace=True)

    gyro_norm = np.sqrt(df_gait['gx']**2 + df_gait['gy']**2 + df_gait['gz']**2)
    
    is_zupt = gyro_norm < ZUPT_GYRO_THRESHOLD
    
    step_events = is_zupt.astype(int).diff()
    step_starts = step_events[step_events == 1].index
    step_ends = step_events[step_events == -1].index

    # ▼▼▼ 여기가 핵심 수정 부분 ▼▼▼
    # 시작과 끝 이벤트의 짝을 맞추는 로직
    if len(step_starts) == 0 or len(step_ends) == 0:
        print("걸음을 감지할 수 없습니다. (시작 또는 끝 이벤트 없음)")
        return

    # 첫 번째 끝이 첫 번째 시작보다 빠르면, 그 끝은 버림
    if step_ends[0] < step_starts[0]:
        step_ends = step_ends[1:]

    # 마지막 시작이 마지막 끝보다 늦으면, 그 시작은 버림
    if step_starts[-1] > step_ends[-1]:
        step_starts = step_starts[:-1]
    
    # 이제 시작과 끝의 개수를 다시 맞춰줌
    min_len = min(len(step_starts), len(step_ends))
    if min_len < 1:
        print("걸음의 짝을 맞출 수 없습니다.")
        return
        
    step_starts = step_starts[:min_len]
    step_ends = step_ends[:min_len]
    # ▲▲▲ 수정 완료 ▲▲▲

    gct_list = []
    for start, end in zip(step_starts, step_ends):
        # 이제 end > start 조건은 항상 만족해야 함
        gct = (end - start) * SAMPLING_PERIOD
        gct_list.append(gct)

    if not gct_list:
        print("GCT를 계산할 수 없습니다. (리스트 비어있음)")
        return

    total_steps = len(gct_list) * 2
    total_time_seconds = (step_ends[-1] - step_starts[0]) * SAMPLING_PERIOD
    
    if total_time_seconds <= 0:
        print("분석에 필요한 총 시간이 부족합니다.")
        return

    cadence = (total_steps / total_time_seconds) * 60
    avg_gct = np.mean(gct_list)

    print("--- 보행 분석 결과 ---")
    print(f"총 걸음 시간: {total_time_seconds} 초")
    print(f"총 감지된 걸음 수: {total_steps} 걸음")
    print(f"평균 케이던스 (분당 걸음 수): {cadence:.2f} steps/min")
    print(f"평균 지면 접촉 시간 (GCT): {avg_gct:.4f} 초")

    # 디버깅용 그래프 (필요시 주석 해제)
    import matplotlib.pyplot as plt
    plt.figure(figsize=(20, 6))
    gyro_norm.plot(label='Gyro Norm')
    plt.axhline(y=ZUPT_GYRO_THRESHOLD, color='r', linestyle='--', label='ZUPT Threshold')
    plt.scatter(step_starts, gyro_norm[step_starts], color='g', s=100, label='Step Start')
    plt.scatter(step_ends, gyro_norm[step_ends], color='k', s=100, label='Step End')
    plt.title('Gyro Norm vs. ZUPT Threshold with Step Events')
    plt.legend()
    plt.show()

# --- 새로운 걸음 수 측정 함수 ---
def detect_steps_with_accel_peaks(df):
    """
    Z축 가속도 데이터의 피크를 감지하여 걸음 수와 케이던스를 계산합니다.
    """
    print("\n--- 보행 분석 시작 (가속도 피크 방식) ---")

    # 1. Z축 가속도 데이터 스무딩 (노이즈 제거)
    # g 단위를 m/s^2 단위로 변환하려면 9.8을 곱하고, 아니면 그냥 사용합니다.
    # 여기서는 센서의 raw g 단위를 그대로 사용한다고 가정합니다.
    az_smooth = df['az'].rolling(window=5, center=True).mean().dropna()
    # az_smooth = df['az']

    # 2. 피크 감지 (가장 핵심적인 부분)
    # height: 피크의 최소 높이. 1.0g(중력) 이상의 충격만 감지하도록 설정. (튜닝 필요)
    # distance: 피크 사이의 최소 간격 (샘플 수). 0.3초 이내에 연속된 피크는 무시. (튜닝 필요)
    # SAMPLING_PERIOD는 0.02 (50Hz)로 가정
    min_peak_height = 1.2  # 1.2g 이상만 걸음으로 인정
    min_step_interval = int(0.3 / SAMPLING_PERIOD) # 최소 0.3초 간격

    peaks, _ = find_peaks(az_smooth, height=min_peak_height, distance=min_step_interval)

    if len(peaks) < 2:
        print("걸음을 충분히 감지할 수 없습니다.")
        return

    # 3. 결과 계산
    total_steps = len(peaks) * 2
    
    # 총 분석 시간 계산 (첫 걸음 ~ 마지막 걸음)
    total_time_seconds = (az_smooth.index[peaks[-1]] - az_smooth.index[peaks[0]]) * SAMPLING_PERIOD
    
    cadence = 0
    if total_time_seconds > 0:
        cadence = (total_steps / total_time_seconds) * 60  # 분당 걸음 수

    print("--- 보행 분석 결과 ---")
    print(f"총 감지된 걸음 수: {total_steps} 걸음")
    if cadence > 0:
        print(f"평균 케이던스 (분당 걸음 수): {cadence:.2f} steps/min")

    # 4. 디버깅용 그래프 출력
    import matplotlib.pyplot as plt
    plt.figure(figsize=(20, 6))
    plt.plot(az_smooth.index, az_smooth, label='Smoothed Z-axis Acceleration')
    plt.plot(az_smooth.index[peaks], az_smooth.iloc[peaks], "x", color='red', markersize=10, label=f'Detected Steps ({total_steps})')
    plt.axhline(y=min_peak_height, color='r', linestyle='--', label=f'Peak Threshold ({min_peak_height}g)')
    plt.title('Step Detection using Z-axis Acceleration Peaks')
    plt.xlabel('Sample Index')
    plt.ylabel('Acceleration (g)')
    plt.legend()
    plt.grid(True)
    plt.show()

    
# ---------------------------
# 메인 코드 실행 (수정됨)
# ---------------------------
if __name__ == "__main__":
    # 1, 2, 3단계: 지형 분석 및 지도 생성
    features, original_data_with_filter = analyze_log_file(INPUT_CSV_PATH)
    
    if features is not None and original_data_with_filter is not None:
        zones = process_and_cluster_zones(features)
        create_map_with_zones(zones, original_data_with_filter)
        
        # 4단계: 보행 안정성 분석 (kalman filter가 적용된 데이터로 수행)
        detect_steps_and_gait_features(original_data_with_filter)

# ---------------------------
# 메인 코드 실행 (수정됨)
# # ---------------------------
# if __name__ == "__main__":
#     print(f"'{INPUT_CSV_PATH}' 파일에서 보행 안정성 분석을 시작합니다.")
    
#     try:
#         full_data = pd.read_csv(INPUT_CSV_PATH) # header 위치는 파일에 맞게 조정
        
#         if full_data.empty:
#             print("오류: CSV 파일이 비어있습니다.")
#         else:
#             # 새로운 가속도 피크 기반 함수 호출
#             detect_steps_with_accel_peaks(full_data)
#             # detect_steps_and_gait_features(full_data)
            
#     except FileNotFoundError:
#         print(f"오류: 파일을 찾을 수 없습니다. -> {INPUT_CSV_PATH}")
#     except Exception as e:
#         print(f"분석 중 오류가 발생했습니다: {e}")