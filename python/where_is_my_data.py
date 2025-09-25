import pandas as pd

# --- 설정 ---
# 1. 분석할 CSV 파일 경로를 지정하세요.
FILE_PATH = 'sensor_log_2025-09-26_03-40-56.csv'  # 👈 여기에 실제 파일명을 입력하세요.

# 2. 아두이노에서 설정한 데이터 전송 주파수 (Hz)
EXPECTED_HZ = 50.0

# --- 프로그램 ---

def analyze_timestamp_gaps(file_path, frequency):
    """CSV 파일의 타임스탬프를 분석하여 데이터 누락을 검증합니다."""
    
    print(f"'{file_path}' 파일을 분석합니다...")
    
    try:
        # CSV 파일을 읽고, 'timestamp' 컬럼을 datetime 객체로 변환
        df = pd.read_csv(file_path, parse_dates=['timestamp'])
    except FileNotFoundError:
        print(f"❗️ 오류: 파일을 찾을 수 없습니다. -> {file_path}")
        return
    except Exception as e:
        print(f"❗️ 오류: 파일을 읽는 중 문제가 발생했습니다. -> {e}")
        return

    if df.empty:
        print("❗️ 파일이 비어있거나 데이터를 읽을 수 없습니다.")
        return

    # 기본 정보 계산
    actual_rows = len(df)
    start_time = df['timestamp'].iloc[0]
    end_time = df['timestamp'].iloc[-1]
    total_duration = end_time - start_time
    total_duration_s = total_duration.total_seconds()
    
    expected_rows = int(total_duration_s * frequency)
    loss_percentage = max(0, (1 - actual_rows / expected_rows)) * 100 if expected_rows > 0 else 0

    print("\n--- 전체 데이터 요약 ---")
    print(f"기록 시작 시간: {start_time}")
    print(f"기록 종료 시간: {end_time}")
    print(f"총 기록 시간: {total_duration} (약 {total_duration_s:.2f}초)")
    print(f"기대 데이터 수: {expected_rows} 개")
    print(f"실제 데이터 수: {actual_rows} 개")
    print(f"데이터 손실률: {loss_percentage:.2f}%")

    # 각 행 사이의 시간 간격 계산
    df['time_diff_s'] = df['timestamp'].diff().dt.total_seconds()

    # 예상 시간 간격 (50Hz -> 0.02초)
    expected_interval_s = 1 / frequency
    
    # 예상 간격의 2배를 초과하는 경우를 '누락'으로 간주
    gap_threshold_s = expected_interval_s * 2
    
    gaps_df = df[df['time_diff_s'] > gap_threshold_s]

    print("\n--- 데이터 누락 상세 분석 ---")
    if gaps_df.empty:
        print("✅ 데이터 누락이 감지되지 않았습니다.")
    else:
        num_gaps = len(gaps_df)
        avg_gap_duration = gaps_df['time_diff_s'].mean()
        max_gap_duration = gaps_df['time_diff_s'].max()

        print(f"❗️ 총 {num_gaps}개의 데이터 누락 구간이 감지되었습니다.")
        print(f"평균 누락 시간: {avg_gap_duration:.2f}초")
        print(f"최대 누락 시간: {max_gap_duration:.2f}초")

        print("\n가장 큰 누락 구간 Top 5 (발생 시점과 누락된 시간):")
        
        # 'time_diff_s'를 기준으로 가장 큰 5개의 누락 구간을 찾음
        top_gaps = gaps_df.nlargest(5, 'time_diff_s')
        
        for index, row in top_gaps.iterrows():
            # 누락은 (이전 행)과 (현재 행) 사이에서 발생했음
            gap_start_time = df['timestamp'].iloc[index - 1]
            gap_duration = row['time_diff_s']
            print(f" - {gap_start_time} 부터 약 {gap_duration:.2f}초 동안 데이터 누락")

if __name__ == '__main__':
    analyze_timestamp_gaps(FILE_PATH, EXPECTED_HZ)