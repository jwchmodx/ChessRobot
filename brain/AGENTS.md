# Brain Module: Chess Engine & Game Logic

체스 게임 로직, Stockfish 엔진 통합, 로봇 암 제어 오케스트레이션을 담당하는 핵심 모듈.

## Module Context

Brain 모듈은 ChessRobot 시스템의 두뇌 역할을 수행하며 다음 서브시스템으로 구성:

**cv/**: 컴퓨터 비전 통합 레이어 (CV 모듈과 연동).
**engine/**: Stockfish 체스 엔진 제어 및 최적 수 계산.
**game/**: 체스 게임 상태 관리, 보드 표시, 이동 분석.
**robot_arm/**: 로봇 암 제어 명령 생성 및 시리얼 통신.
**timer/**: 체스 타이머 제어 (7세그먼트 디스플레이).
**aicv/**: AI 모델 학습 데이터 (이미지 샘플).

## Tech Stack & Constraints

### Core Dependencies

```
flask: 웹 인터페이스 및 API 서버.
numpy: 배열 연산 및 좌표 변환.
opencv-python: CV 모듈 연동 및 이미지 처리.
python-chess: 체스 규칙, FEN 파싱, 합법적 수 검증.
pyserial: 아두이노 시리얼 통신.
picamera2: 라즈베리파이 카메라 (Raspberry Pi OS only).
```

### Stockfish Engine

**위치 확인:**
```bash
which stockfish
```

**환경변수 설정 (필요 시):**
```bash
export STOCKFISH_PATH="/usr/local/bin/stockfish"
```

**코드 내 경로 지정:**
```python
import chess.engine
engine = chess.engine.SimpleEngine.popen_uci("/usr/local/bin/stockfish")
```

### 라이브러리 제약

**DO:**
- python-chess 라이브러리로 모든 체스 규칙 검증.
- Stockfish 엔진 응답 타임아웃 최소 5초 설정.
- 시리얼 통신은 pyserial 사용 (baud rate 9600 고정).

**DON'T:**
- 체스 규칙을 직접 구현 금지. python-chess 라이브러리 사용 필수.
- Stockfish 엔진을 여러 스레드에서 동시 호출 금지.
- CV 모듈의 내부 함수를 직접 수정 금지. cv/ 레이어를 통해서만 호출.

## Implementation Patterns

### Game State Management

**FEN String 사용:**
```python
import chess

# 초기 보드
board = chess.Board()
print(board.fen())  # "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# 수 적용
board.push_san("e4")  # e2e4
print(board.fen())
```

**합법적 수 검증:**
```python
move = chess.Move.from_uci("e2e4")
if move in board.legal_moves:
    board.push(move)
else:
    print("불법적인 수")
```

### Stockfish Engine Integration

**엔진 초기화 (싱글톤 패턴):**
```python
import chess.engine

class EngineManager:
    _instance = None
    _engine = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._engine = chess.engine.SimpleEngine.popen_uci("/usr/local/bin/stockfish")
        return cls._instance
    
    def get_best_move(self, board, time_limit=5.0):
        result = self._engine.play(board, chess.engine.Limit(time=time_limit))
        return result.move
    
    def close(self):
        if self._engine:
            self._engine.quit()
```

**최적 수 요청:**
```python
manager = EngineManager.get_instance()
best_move = manager.get_best_move(board, time_limit=5.0)
print(best_move.uci())  # "e2e4"
```

### Robot Arm Coordination

**좌표 변환 파이프라인:**
```python
# 1. UCI 표기법을 보드 좌표로 변환
def uci_to_coords(uci_move):
    # "e2e4" -> (4, 1) to (4, 3)
    from_square = chess.SQUARE_NAMES.index(uci_move[:2])
    to_square = chess.SQUARE_NAMES.index(uci_move[2:4])
    
    from_coords = (from_square % 8, from_square // 8)
    to_coords = (to_square % 8, to_square // 8)
    
    return from_coords, to_coords

# 2. 보드 좌표를 실제 물리 좌표로 변환
def board_to_physical(board_x, board_y):
    # 체스판 칸 크기 (mm)
    SQUARE_SIZE = 50.0
    # 원점 오프셋
    ORIGIN_X = 100.0
    ORIGIN_Y = 100.0
    
    physical_x = ORIGIN_X + board_x * SQUARE_SIZE
    physical_y = ORIGIN_Y + board_y * SQUARE_SIZE
    
    return physical_x, physical_y

# 3. 아두이노로 좌표 전송
def send_to_arduino(serial_port, x, y, z=50.0):
    command = f"{x},{y},{z}\n"
    serial_port.write(command.encode())
    serial_port.flush()
    
    # 응답 대기
    time.sleep(0.1)
    response = serial_port.readline().decode().strip()
    return response
```

### Flask Web Interface

**API 엔드포인트 구조:**
```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route('/api/game/start', methods=['POST'])
def start_game():
    data = request.json
    color = data.get('color', 'white')
    difficulty = data.get('difficulty', 10)
    # 게임 초기화 로직
    return jsonify({'status': 'ok', 'fen': board.fen()})

@app.route('/api/game/move', methods=['POST'])
def make_move():
    data = request.json
    uci_move = data.get('move')
    # 수 검증 및 적용
    return jsonify({'status': 'ok', 'fen': board.fen()})

@app.route('/api/engine/move', methods=['GET'])
def get_engine_move():
    best_move = manager.get_best_move(board)
    return jsonify({'move': best_move.uci()})
```

### CV Module Integration

**CV 파이프라인 호출 (cv/cv_manager.py 참조):**
```python
from cv.cv_manager import CVManager

cv_manager = CVManager()

# 현재 보드 상태 인식
detected_fen = cv_manager.detect_board()

# FEN 검증
if chess.Board(detected_fen).is_valid():
    board.set_fen(detected_fen)
else:
    print("잘못된 FEN 문자열")
```

## Testing Strategy

### Unit Testing

**테스트 파일 구조:**
```
brain/
  tests/
    test_engine_manager.py
    test_game_state.py
    test_robot_controller.py
```

**Mock Stockfish Engine:**
```python
import unittest
from unittest.mock import MagicMock, patch

class TestEngineManager(unittest.TestCase):
    @patch('chess.engine.SimpleEngine.popen_uci')
    def test_get_best_move(self, mock_popen):
        mock_engine = MagicMock()
        mock_engine.play.return_value.move = chess.Move.from_uci("e2e4")
        mock_popen.return_value = mock_engine
        
        manager = EngineManager.get_instance()
        move = manager.get_best_move(chess.Board())
        
        self.assertEqual(move.uci(), "e2e4")
```

**Mock Serial Port:**
```python
class MockSerial:
    def __init__(self, port, baudrate):
        self.buffer = []
    
    def write(self, data):
        self.buffer.append(data)
    
    def readline(self):
        return b"OK\n"
```

### Integration Testing

```bash
# 웹 서버 실행
python chess_web_game.py

# 브라우저에서 테스트
curl -X POST http://localhost:5000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{"color": "white", "difficulty": 10}'
```

## Local Golden Rules

### Critical Do's

1. **FEN 검증**: CV 모듈에서 받은 FEN 문자열은 반드시 python-chess로 유효성 검증.
2. **엔진 타임아웃**: Stockfish 응답이 10초 이상 걸리면 타임아웃 처리.
3. **시리얼 통신 재시도**: 아두이노 응답 실패 시 최대 3회 재시도.
4. **좌표 범위 검증**: 물리 좌표가 로봇 암 작업 영역을 벗어나면 명령 거부.
5. **게임 상태 동기화**: 로봇 암 이동 완료 후에만 게임 상태 업데이트.

### Critical Don'ts

1. **절대 불법적인 수를 아두이노로 전송 금지**: python-chess 검증 없이 명령 전송 금지.
2. **CV 파이프라인 블로킹 금지**: 이미지 처리 중 Flask 서버가 멈추지 않도록 비동기 처리.
3. **Stockfish 다중 인스턴스 금지**: 싱글톤 패턴으로 하나의 엔진만 사용.
4. **하드코딩된 체스판 크기 금지**: 설정 파일 또는 캘리브레이션으로 동적 설정.
5. **예외 처리 누락 금지**: 시리얼 통신, 엔진 호출 등 모든 외부 의존성에 try-except 적용.

## File Naming & Structure Conventions

**Python 모듈:**
- engine_manager.py: Stockfish 엔진 관리 싱글톤.
- game_state.py: 게임 상태 및 보드 관리.
- robot_arm_controller.py: 로봇 암 명령 생성 및 시리얼 통신.
- board_display.py: 터미널 또는 웹 UI용 보드 렌더링.

**클래스 네이밍:**
- EngineManager: 엔진 관리자.
- GameState: 게임 상태 관리.
- RobotArmController: 로봇 제어기.

**함수 네이밍:**
- get_best_move(): 최적 수 계산.
- uci_to_coords(): UCI 표기법 변환.
- send_command(): 시리얼 명령 전송.

## Operational Commands

### 웹 서버 실행
```bash
cd brain
python chess_web_game.py
# 접속: http://localhost:5000
```

### 터미널 체스 실행
```bash
python brain/terminal_chess.py
```

### 테스트 실행
```bash
cd brain
python -m pytest tests/
```

### 특수 이동 테스트
```bash
python brain/test_special_moves.py
```

## Module Dependencies

**Brain -> CV:**
- cv/cv_manager.py를 통해 보드 상태 요청.
- 와핑된 이미지에서 FEN 추출.

**Brain -> Motion:**
- robot_arm/ 모듈에서 좌표 계산 후 시리얼 전송.
- Arduino IK 계산 결과 대기.

**Brain -> Timer:**
- timer/timer_manager.py로 게임 시간 제어.
- 7세그먼트 디스플레이 업데이트.

## Troubleshooting

**Stockfish를 찾을 수 없는 경우:**
```bash
# macOS
brew install stockfish

# Ubuntu
sudo apt-get install stockfish

# 경로 확인
which stockfish
```

**시리얼 포트 접근 권한 오류:**
```bash
sudo chmod 666 /dev/ttyUSB0
# 또는
sudo usermod -a -G dialout $USER
```

**Flask 포트 충돌:**
```python
# chess_web_game.py
app.run(debug=True, host='0.0.0.0', port=5001)
```

**PiCamera2 설치 (Raspberry Pi only):**
```bash
sudo apt install -y python3-picamera2
```

## Performance Optimization

1. **Stockfish Skill Level**: 난이도 조절로 응답 속도 개선 (5-20 범위).
2. **CV 파이프라인 캐싱**: 마커 변환 행렬을 메모리에 캐싱하여 재계산 방지.
3. **비동기 로봇 제어**: 아두이노 명령 전송과 웹 UI 업데이트를 비동기 처리.
4. **멀티스레딩 주의**: Stockfish 엔진은 스레드 안전하지 않음. 락(Lock) 사용 필수.
