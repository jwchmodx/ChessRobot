#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로봇팔 제어 모듈
체스 움직임을 분석하여 로봇팔에 적절한 명령을 전송
명령을 단위별로 분리하고 아두이노 응답을 기다리면서 순차 실행
"""

import chess
import serial
import time
from typing import Dict, Optional, Tuple, List

class RobotArmController:
    """로봇팔 제어 클래스"""
    
    def __init__(self, enabled: bool = True, port: str = '/dev/ttyUSB1', baudrate: int = 9600):
        self.enabled = enabled
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.is_connected = False
        self.is_moving = False
        
        # 기물 타입 매핑
        self.piece_names = {
            chess.PAWN: 'pawn',
            chess.KNIGHT: 'knight', 
            chess.BISHOP: 'bishop',
            chess.ROOK: 'rook',
            chess.QUEEN: 'queen',
            chess.KING: 'king'
        }
        
        print(f"🤖 로봇팔 컨트롤러 초기화:")
        print(f"   활성화: {self.enabled}")
        print(f"   포트: {self.port}")
        print(f"   통신속도: {self.baudrate}")
    
    def connect(self) -> bool:
        """시리얼 연결 시도"""
        if not self.enabled:
            print("🤖 로봇팔이 비활성화되어 있습니다.")
            return False
        
        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            self.is_connected = True
            print(f"✅ 로봇팔 연결 성공: {self.port}")
            return True
        except Exception as e:
            print(f"❌ 로봇팔 연결 실패: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """시리얼 연결 해제"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.is_connected = False
        self.is_moving = False
        print("🔌 로봇팔 연결 해제됨")
    
    def _generate_move_commands(self, move_type: Dict, move_uci: str) -> List[str]:
        """움직임 타입에 따라 명령 리스트 생성.

        IKtest.ino 스케치와 호환되도록, 기본은 체스 좌표 문자열을 전송한다.
        - 일반 수: 'e2e4' → ['e2e4']               (from+to 한 번에 전송)
        - 기물 잡기: 'e2e4' (capture) → ['e4cap', 'e2e4']
          (1) 목적지 칸(e4)에 있는 말을 먼저 잡는 명령
          (2) 실제 이동(from→to)을 한 번에 전송
        - 캐슬링: 킹과 룩 두 번 이동
        - 앙파상: 잡힌 폰 제거 + 폰 이동
        """
        if not move_uci or len(move_uci) < 4:
            return []

        from_square = move_uci[:2]
        to_square = move_uci[2:4]

        # 캡처/특수 규칙에 따라 명령 구성
        commands: List[str] = []

        # 1. 캐슬링: 킹과 룩을 각각 이동
        if move_type.get("is_castling"):
            # 킹 이동
            commands.append(f"{from_square}{to_square}")
            
            # 룩 이동
            if to_square == "c8":  # 흑색 퀸사이드 캐슬링
                commands.append("a8d8")
            elif to_square == "g8":  # 흑색 킹사이드 캐슬링
                commands.append("h8f8")
            elif to_square == "c1":  # 백색 퀸사이드 캐슬링
                commands.append("a1d1")
            elif to_square == "g1":  # 백색 킹사이드 캐슬링
                commands.append("h1f1")
        
        # 2. 앙파상: 잡힌 폰의 위치를 정확히 계산
        elif move_type.get("is_en_passant"):
            from_file = from_square[0]
            from_rank = from_square[1]
            to_file = to_square[0]
            to_rank = to_square[1]
            
            # 잡힌 폰은 to_square와 같은 파일, from_square와 같은 랭크에 있음
            capture_square = f"{to_file}{from_rank}"
            
            commands.append(f"{capture_square}cap")  # 잡힌 폰 제거
            commands.append(f"{from_square}{to_square}")  # 폰 이동
        
        # 3. 일반 캡처
        elif move_type.get("is_capture"):
            commands.append(f"{to_square}cap")  # 목적지 기물 제거
            commands.append(f"{from_square}{to_square}")  # 이동
        
        # 4. 일반 이동
        else:
            commands.append(f"{from_square}{to_square}")

        return commands
    
    def _send_single_command(self, command: str, wait_for_completion: bool = True, timeout: float = 30.0) -> bool:
        """단일 명령 전송 및 완료 신호 대기.

        Args:
            command: 전송할 명령
            wait_for_completion: 완료 신호를 기다릴지 여부 (기본값: True)
            timeout: 완료 신호 대기 최대 시간 (초)
        """
        if not self.is_connected:
            print("🤖 로봇팔이 연결되지 않았습니다. 명령 전송을 건너뜁니다.")
            return True  # 연결되지 않아도 성공으로 처리
        
        try:
            # 실제로 어떤 명령을 보내는지 명확히 로그로 출력
            print(f"📡 명령 전송: {command}")
            encoded = f"{command}\n".encode()
            print(f"   [DEBUG] 전송 바이트: {encoded!r}")
            
            # 명령 전송
            if self.serial_connection and self.serial_connection.is_open:
                self.serial_connection.write(encoded)
                self.serial_connection.flush()

                if wait_for_completion:
                    # 완료 신호 대기 (MOVE_COMPLETE 또는 DONE 또는 타이머 버튼)
                    print("⏳ 로봇팔 완료 신호 대기 중...")
                    start_time = time.time()
                    completion_received = False
                    
                    while time.time() - start_time < timeout:
                        # 로봇팔 완료 신호 체크
                        if self.serial_connection.in_waiting:
                            response = self.serial_connection.readline().decode(errors="ignore").strip()
                            if response:
                                # 로봇팔에서 받은 모든 라인을 그대로 출력
                                print(f"🤖 로봇팔 응답 수신: {response}")
                                # 완료 신호 확인
                                upper_response = response.upper()
                                # 아두이노에서 'movecomplete', 'MOVE_COMPLETE' 등으로 보낼 수 있으므로 둘 다 허용
                                completion_keywords = [
                                    'MOVE_COMPLETE',   # 기존 형식 (언더스코어 포함)
                                    'MOVECOMPLETE',    # 언더스코어 없이 붙여쓴 형식
                                    'DONE',
                                    'COMPLETE',
                                    'READY',
                                    'movecomplete',
                                ]
                                if any(keyword in upper_response for keyword in completion_keywords):
                                    completion_received = True
                                    print("✅ 로봇팔 완료 신호 수신")
                                    break
                        
                        # 타이머 버튼 체크 (P2 = 흰색 종료)
                        try:
                            from timer.timer_manager import check_timer_button
                            timer_signal = check_timer_button()
                            if timer_signal == "P2":  # 흰색 종료 버튼
                                completion_received = True
                                print("✅ 타이머 버튼 (P2) 감지 - 로봇팔 완료로 간주")
                                break
                        except Exception:
                            pass  # 타이머 연결 안 되어 있으면 무시
                        
                        time.sleep(0.1)
                    
                    if not completion_received:
                        print(f"⚠️ 완료 신호를 {timeout}초 내에 받지 못했습니다. 계속 진행합니다.")
                else:
                    # 완료 신호를 기다리지 않는 경우 (짧은 응답만 확인)
                    start_time = time.time()
                    while time.time() - start_time < 0.2:
                        if self.serial_connection.in_waiting:
                            response = self.serial_connection.readline().decode(errors="ignore").strip()
                            if response:
                                print(f"🤖 로봇팔 응답: {response}")
                        else:
                            time.sleep(0.02)

                return True
            else:
                print("❌ 시리얼 연결이 열려있지 않습니다.")
                return False
                
        except Exception as e:
            print(f"[!] 명령 전송 실패: {e}")
            return False
    
    def execute_move(self, move_type: Dict, move_uci: str) -> bool:
        """움직임 분석 및 로봇팔 명령 순차 실행"""
        if not self.enabled:
            return False
        
        if self.is_moving:
            print("🤖 로봇팔이 이미 움직이는 중입니다.")
            return False
        
        # 움직임 분석
        commands = self._generate_move_commands(move_type, move_uci)
        if not commands:
            print("❌ 움직임 분석 실패")
            return False
        
        print(f"🤖 움직임 분석 완료: {len(commands)}개 명령")
        for i, cmd in enumerate(commands, 1):
            print(f"   {i}. {cmd}")
        
        # 로봇팔 연결 상태 확인
        if not self.is_connected:
            print("🤖 로봇팔이 연결되지 않았습니다. 명령만 표시합니다.")
            print("📋 실행될 명령들:")
            for i, command in enumerate(commands, 1):
                print(f"   {i}. {command}")
            print("✅ 명령 분석 완료 (실제 실행 없음)")
            return True
        
        # 로봇팔 움직임 시작
        self.is_moving = True
        print("🤖 로봇이 움직이는 중...")
        
        try:
            # 명령들을 순차적으로 실행
            for i, command in enumerate(commands, 1):
                print(f"🤖 명령 {i}/{len(commands)} 실행 중: {command}")
                
                # 완료 신호 기다리지 않고 바로 전송
                if not self._send_single_command(command, wait_for_completion=False):
                    print(f"❌ 명령 {i} 실행 실패")
                    self.is_moving = False
                    return False
                
                # 마지막 명령이 아니면 대기 (로봇팔이 동작할 시간 필요)
                if i < len(commands):
                    print(f"   ⏳ 다음 명령 전까지 대기 중...")
                    time.sleep(3.0)  # 로봇팔이 충분히 움직일 시간 제공

            # 모든 이동이 끝나면 제로 포지션으로 복귀 명령 전송
            # 타이머 버튼(흰색 종료)을 기다림
            print("🤖 모든 이동 완료, 제로 포지션으로 복귀 명령 전송: zero")
            self._send_single_command("zero", wait_for_completion=True)
            
            print("✅ 모든 명령 실행 완료!")
            return True
            
        except Exception as e:
            print(f"[!] 명령 실행 중 오류: {e}")
            return False
        finally:
            self.is_moving = False
    
    def get_move_description(self, move_type: Dict, move_uci: str) -> str:
        """움직임에 대한 설명 반환"""
        if not move_type or not move_uci:
            return "알 수 없는 움직임"
        
        if move_type.get('is_castling'):
            return "캐슬링"
        elif move_type.get('is_en_passant'):
            return "앙파상"
        elif move_type.get('is_capture'):
            return "기물 잡기"
        elif move_type.get('is_promotion'):
            return "프로모션"
        else:
            return "일반 이동"
    
    def configure(self, enabled: bool = None, port: str = None, baudrate: int = None):
        """로봇팔 설정 조정"""
        if enabled is not None:
            self.enabled = enabled
        if port is not None:
            self.port = port
        if baudrate is not None:
            self.baudrate = baudrate
        
        print(f"🤖 로봇팔 설정 업데이트:")
        print(f"   활성화: {self.enabled}")
        print(f"   포트: {self.port}")
        print(f"   통신속도: {self.baudrate}")
    
    def get_status(self) -> Dict:
        """로봇팔 상태 정보 반환"""
        return {
            'enabled': self.enabled,
            'port': self.port,
            'baudrate': self.baudrate,
            'is_connected': self.is_connected,
            'is_moving': self.is_moving,
            'connection': 'connected' if self.is_connected else 'disconnected',
            'status': 'moving' if self.is_moving else 'idle'
        }
    
    def test_connection(self) -> bool:
        """연결 테스트"""
        if not self.enabled:
            print("🤖 로봇팔이 비활성화되어 있습니다.")
            return False
        
        if self.connect():
            self.disconnect()
            return True
        return False
    
    def move_to_zero_position(self) -> bool:
        """로봇팔을 제로 포지션으로 이동"""
        if not self.enabled:
            print("🤖 로봇팔이 비활성화되어 있습니다.")
            return False
        
        if not self.is_connected:
            print("🤖 로봇팔이 연결되지 않았습니다. 제로 포지션 이동을 건너뜁니다.")
            return True  # 연결되지 않아도 성공으로 처리
        
        print("🤖 로봇팔을 제로 포지션으로 이동 중...")
        # 완료 신호 기다리지 않음 - 명령만 전송
        success = self._send_single_command("zero", wait_for_completion=False)
        if success:
            print("✅ 로봇팔 제로 포지션 이동 명령 전송")
        else:
            print("⚠️ 로봇팔 제로 포지션 이동 명령 실패 (계속 진행)")
        return success


# 전역 인스턴스
_robot_controller = RobotArmController()

def get_robot_controller() -> RobotArmController:
    """전역 로봇팔 컨트롤러 인스턴스 반환"""
    return _robot_controller

def init_robot_arm(enabled: bool = True, port: str = '/dev/ttyUSB1', baudrate: int = 9600) -> bool:
    """로봇팔 초기화"""
    global _robot_controller
    _robot_controller = RobotArmController(enabled, port, baudrate)
    return _robot_controller.enabled

def connect_robot_arm() -> bool:
    """로봇팔 연결"""
    return _robot_controller.connect()

def disconnect_robot_arm():
    """로봇팔 연결 해제"""
    _robot_controller.disconnect()

def execute_robot_move(move_type: Dict, move_uci: str) -> bool:
    """로봇팔 움직임 실행"""
    return _robot_controller.execute_move(move_type, move_uci)

def get_move_description(move_type: Dict, move_uci: str) -> str:
    """움직임 설명 반환"""
    return _robot_controller.get_move_description(move_type, move_uci)

def is_robot_moving() -> bool:
    """로봇팔이 움직이는 중인지 확인"""
    return _robot_controller.is_moving

def configure_robot_arm(enabled: bool = None, port: str = None, baudrate: int = None):
    """로봇팔 설정 조정"""
    _robot_controller.configure(enabled, port, baudrate)

def get_robot_status() -> Dict:
    """로봇팔 상태 정보"""
    return _robot_controller.get_status()

def test_robot_connection() -> bool:
    """로봇팔 연결 테스트"""
    return _robot_controller.test_connection()

def move_robot_to_zero_position() -> bool:
    """로봇팔을 제로 포지션으로 이동"""
    return _robot_controller.move_to_zero_position()
