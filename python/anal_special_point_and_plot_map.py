import pandas as pd
import numpy as np
import folium
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise

# ---------------------------
# 설정
# ---------------------------
INPUT_CSV_PATH = 'sensor_log_2025-09-25_14-15-35.csv' # 실제 파일명으로 변경하세요.
OUTPUT_ZONES_CSV_PATH = 'special_zones_kalman.csv'
OUTPUT_MAP_PATH = 'mobility_map_kalman.html'

WINDOW_SIZE = 10
STEP_SIZE = 5

VAR_THRESHOLD = 0.03
PITCH_THRESHOLD = 0.4
MIN_POINTS_IN_CLUSTER = 3
ZONE_RADIUS = 5

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

# ---------------------------
# 메인 코드 실행 (수정됨)
# ---------------------------
if __name__ == "__main__":
    # analyze_log_file이 두 개의 값을 반환하도록 수정됨
    features, original_data_with_filter = analyze_log_file(INPUT_CSV_PATH)
    
    if features is not None:
        zones = process_and_cluster_zones(features)
        create_map_with_zones(zones, original_data_with_filter)