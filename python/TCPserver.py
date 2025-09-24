import socket

HOST = '0.0.0.0'  # 모든 인터페이스에서 수신
PORT = 65000       # 아두이노에서 연결할 포트

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    print("Waiting for Arduino...")
    conn, addr = s.accept()
    print(f"Connected by {addr}")

    with conn:
        while True:
            data = conn.recv(1024).decode('utf-8')
            print(data.strip())  # 여기서 데이터 저장/실시간 처리 가능
            frame = data.strip().split(',') # lat, lon, ax, ay, az, gx, gy, gz, mx, my, mz
            