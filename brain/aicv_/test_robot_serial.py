#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로봇팔 아두이노 단독 시리얼 테스트 스크립트.

 - /dev/ttyUSB0 로 연결 시도
 - 사용자가 입력한 문자열을 그대로 전송 (개행 포함)
 - 아두이노에서 오는 모든 응답을 그대로 출력

사용법:
    python3 /home/chess/Desktop/ChessRobot/tools/test_robot_serial.py
"""

import sys
import time

import serial


PORT = "/dev/ttyUSB0"
BAUDRATE = 9600


def main() -> None:
    print(f"[TEST] 로봇팔 아두이노 시리얼 테스트 시작")
    print(f"[TEST] 포트: {PORT}, 보레이트: {BAUDRATE}")

    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    except Exception as exc:
        print(f"[ERROR] 시리얼 포트 열기 실패: {exc}")
        sys.exit(1)

    print("[TEST] 연결 성공. 테스트 명령을 입력하세요.")
    print("       예) moveto c7c5  또는  c7c5  등")
    print("       'quit' 입력 시 종료.")

    try:
        while True:
            # 먼저 수신 버퍼에 쌓인 응답을 모두 읽어 보여줌
            if ser.in_waiting:
                try:
                    line = ser.readline().decode(errors="ignore").strip()
                    if line:
                        print(f"[RX] {line}")
                except Exception as exc:
                    print(f"[WARN] 수신 중 오류: {exc}")

            # 사용자 입력 받아서 전송
            try:
                user_input = input("[TX] 보낼 문자열 입력: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[TEST] 입력 종료")
                break

            if not user_input:
                continue
            if user_input.lower() in ("q", "quit", "exit"):
                print("[TEST] 종료 명령 입력, 테스트를 종료합니다.")
                break

            data = f"{user_input}\n".encode()
            print(f"[DEBUG] 전송 바이트: {data!r}")
            try:
                ser.write(data)
                ser.flush()
            except Exception as exc:
                print(f"[ERROR] 전송 실패: {exc}")
                break

            # 전송 후 잠깐 대기하면서 응답 읽기
            end_time = time.time() + 2.0
            while time.time() < end_time:
                if ser.in_waiting:
                    try:
                        line = ser.readline().decode(errors="ignore").strip()
                        if line:
                            print(f"[RX] {line}")
                    except Exception as exc:
                        print(f"[WARN] 수신 중 오류: {exc}")
                        break
                else:
                    time.sleep(0.05)

    finally:
        try:
            ser.close()
        except Exception:
            pass
        print("[TEST] 시리얼 포트 닫음")


if __name__ == "__main__":
    main()


