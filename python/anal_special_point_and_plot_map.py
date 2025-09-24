import pandas as pd
import numpy as np
import folium

# ---------------------------
# 설정
# ---------------------------
# 분석할 로그 파일 경로
INPUT_CSV_PATH = 'sensor_log_2025-09-25_02-58-05.csv' # 실제 파일명으로 변경하세요.

# 클러스터링된 존 정보를 저장할 파일 경로
OUTPUT_ZONES_CSV_PATH = 'special_zones.csv'

# 지도 결과물을 저장할 파일 경로
OUTPUT_MAP_PATH = 'mobility_map_zones.html'

# 특징 추출 설정 (실시간 코드와 동일하게)
WINDOW_SIZE = 10
STEP_SIZE = 5

# 특이 지점 판단 임계값 (Threshold)
VAR_THRESHOLD = 0.02
PITCH_THRESHOLD = 0.25

# ▼▼▼ 새로 추가된 튜닝 설정값 ▼▼▼
# 클러스터를 구성하는 최소 지점 수 (이 값보다 작으면 노이즈로 간주하고 무시)
MIN_POINTS_IN_CLUSTER = 3
# 지도에 표시할 원의 반경 (미터 단위)
ZONE_RADIUS = 10 # GPS 오차 등을 감안한 반경

# ---------------------------
# 1. CSV 파일 로드 및 특징 추출 (이전과 동일)
# ---------------------------
def analyze_log_file(filepath):
    """
    센서 로그 파일을 읽어들여, 슬라이딩 윈도우 방식으로 특징을 추출합니다.
    """
    print(f"'{filepath}' 파일을 분석합니다...")
    try:
        df = pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"오류: 파일을 찾을 수 없습니다. -> {filepath}")
        return None

    features_list = []
    
    # 이전에 만들었던 특징 추출 로직을 그대로 사용합니다.
    for i in range(0, len(df) - WINDOW_SIZE, STEP_SIZE):
        window = df.iloc[i : i + WINDOW_SIZE].copy()

        # 이동 평균 적용
        for col in ['ax', 'ay', 'az']:
            window[f'{col}_smooth'] = window[col].rolling(window=2).mean()
        window.dropna(inplace=True)
        
        if window.empty:
            continue

        # z축 분산 계산
        z_acc_var = window['az_smooth'].var()
        
        # 평균 기울기 계산 (atan2 방식)
        pitch_y_rad = np.mean(np.arctan2(window['ax_smooth'], np.sqrt(window['ay_smooth']**2 + window['az_smooth']**2)))
        mean_pitch_absolute = np.abs(pitch_y_rad)
        
        # 해당 윈도우의 중앙 GPS 좌표와 함께 결과 저장
        features_list.append({
            'z_variance': z_acc_var,
            'mean_pitch': mean_pitch_absolute,
            'lat': window['lat'].median(),
            'lon': window['lon'].median()
        })
        
    return pd.DataFrame(features_list)

# ---------------------------
# 2. 특이 지점 클러스터링 및 존(Zone) 정보 생성 (새로운 함수)
# ---------------------------
def process_and_cluster_zones(feature_df):
    """
    특징 데이터프레임에서 연속된 특이 지점을 클러스터링하여 존(Zone) 정보를 생성합니다.
    """
    if feature_df is None: return None

    # 임계값을 넘는지 여부를 boolean 값으로 표시
    feature_df['is_stair'] = feature_df['z_variance'] > VAR_THRESHOLD
    feature_df['is_ramp'] = feature_df['mean_pitch'] > PITCH_THRESHOLD

    # 연속된 True/False 그룹에 고유 ID 부여 (cumsum 트릭)
    feature_df['stair_cluster_id'] = (feature_df['is_stair'].diff() != 0).cumsum()
    feature_df['ramp_cluster_id'] = (feature_df['is_ramp'].diff() != 0).cumsum()

    zone_summary_list = []
    
    # 계단/단차 클러스터 처리
    stair_clusters = feature_df[feature_df['is_stair']].groupby('stair_cluster_id')
    for cluster_id, cluster_df in stair_clusters:
        if len(cluster_df) >= MIN_POINTS_IN_CLUSTER:
            zone_summary_list.append({
                'type': 'Stair/Bump Zone',
                'lat': cluster_df['lat'].mean(),
                'lon': cluster_df['lon'].mean(),
                'points_count': len(cluster_df),
                'max_variance': cluster_df['z_variance'].max(),
                'avg_pitch': cluster_df['mean_pitch'].mean()
            })
            
    # 경사로 클러스터 처리
    ramp_clusters = feature_df[feature_df['is_ramp']].groupby('ramp_cluster_id')
    for cluster_id, cluster_df in ramp_clusters:
        if len(cluster_df) >= MIN_POINTS_IN_CLUSTER:
            # 단, 이 그룹이 이미 계단 그룹으로 처리되지 않았는지 확인
            # (계단 그룹의 평균 pitch가 경사로 기준을 넘을 수 있기 때문)
            is_already_processed_as_stair = (
                (cluster_df['z_variance'] > VAR_THRESHOLD).any() and 
                (cluster_df['z_variance'].mean() > VAR_THRESHOLD)
            )
            if not is_already_processed_as_stair:
                 zone_summary_list.append({
                    'type': 'Ramp Zone',
                    'lat': cluster_df['lat'].mean(),
                    'lon': cluster_df['lon'].mean(),
                    'points_count': len(cluster_df),
                    'max_variance': cluster_df['z_variance'].max(),
                    'avg_pitch': cluster_df['mean_pitch'].mean()
                })

    if not zone_summary_list:
        print("분석 결과, 기준을 만족하는 특이 구역(Zone)이 발견되지 않았습니다.")
        return None
        
    zones_df = pd.DataFrame(zone_summary_list)
    print(f"\n총 {len(zones_df)}개의 특이 구역(Zone)을 발견했습니다.")
    print(zones_df)
    
    zones_df.to_csv(OUTPUT_ZONES_CSV_PATH, index=False)
    print(f"특이 구역 정보를 '{OUTPUT_ZONES_CSV_PATH}' 파일에 저장했습니다.")
    
    return zones_df

# ---------------------------
# 3. Folium으로 존(Zone) 시각화 (새로운 함수)
# ---------------------------
def create_map_with_zones(zones_df):
    """
    클러스터링된 존(Zone) 정보를 받아 Folium 지도에 원으로 표시합니다.
    """
    if zones_df is None or zones_df.empty:
        print("지도에 표시할 구역이 없어 시각화를 건너뜁니다.")
        return

    map_center = [zones_df['lat'].iloc[0], zones_df['lon'].iloc[0]]
    m = folium.Map(location=map_center, zoom_start=18)

    for idx, row in zones_df.iterrows():
        zone_type = row['type']
        color = 'red' if 'Stair' in zone_type else 'orange'
        
        popup_html = f"""
        <b>Type:</b> {zone_type}<br>
        <b>Points Count:</b> {row['points_count']}<br>
        <b>Max Variance:</b> {row['max_variance']:.4f}<br>
        <b>Avg Pitch:</b> {row['avg_pitch']:.4f}<br>
        <b>Center Coords:</b> ({row['lat']:.6f}, {row['lon']:.6f})
        """
        
        # 원(Circle)으로 존 표시
        folium.Circle(
            location=[row['lat'], row['lon']],
            radius=ZONE_RADIUS,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.3,
            popup=folium.Popup(popup_html, max_width=250)
        ).add_to(m)

    m.save(OUTPUT_MAP_PATH)
    print(f"\n구역 지도를 '{OUTPUT_MAP_PATH}' 파일에 성공적으로 저장했습니다.")
    print("해당 파일을 웹 브라우저로 열어 결과를 확인하세요!")

# ---------------------------
# 메인 코드 실행
# ---------------------------
if __name__ == "__main__":
    features = analyze_log_file(INPUT_CSV_PATH)
    zones = process_and_cluster_zones(features)
    create_map_with_zones(zones)