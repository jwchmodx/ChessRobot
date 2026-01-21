# Init Module: Hardware Initialization & Timer

라즈베리파이-아두이노 시리얼 연결 초기화 및 7세그먼트 체스 타이머 제어.

## Module Context

Init 모듈은 ChessRobot 시스템의 하드웨어 초기화 및 주변 장치 제어:

**rasp-ardu/**: 라즈베리파이와 아두이노 시리얼 통신 테스트.
**timer/**: 7세그먼트 디스플레이 기반 체스 타이머 (Arduino).
**head.stl**: 3D 프린팅용 타이머 하우징 모델.

## Tech Stack & Constraints

### Serial Communication

**Python (Raspberry Pi):**
```
pyserial: 시리얼 통신 라이브러리.
```

**Arduino:**
- Serial.begin(9600): 9600 baud rate.
- Serial.available(): 수신 데이터 확인.
- Serial.read() / Serial.println(): 데이터 송수신.

### Timer Hardware

**7-Segment Display:**
- 타입: 4-digit common cathode 또는 common anode.
- 제어: TM1637 드라이버 IC (2-wire 통신).
- 전원: 5V.

**Arduino Pins:**
- CLK: Digital pin 2.
- DIO: Digital pin 3.

## Implementation Patterns

### Raspberry Pi - Arduino Connection Test

**connect_rasp.py:**
```python
#!/usr/bin/env python3
import serial
import time

def test_serial_connection(port='/dev/ttyUSB0', baudrate=9600):
    try:
        ser = serial.Serial(port, baudrate, timeout=5)
        time.sleep(2)  # Arduino 초기화 대기
        
        print(f"Connected to {port} at {baudrate} baud")
        
        # 테스트 메시지 전송
        test_message = "HELLO\n"
        ser.write(test_message.encode())
        print(f"Sent: {test_message.strip()}")
        
        # 응답 수신
        response = ser.readline().decode().strip()
        print(f"Received: {response}")
        
        ser.close()
        return True
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == '__main__':
    # 포트 자동 감지
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
    
    for port in ports:
        print(f"Trying {port}...")
        if test_serial_connection(port):
            print(f"Success on {port}")
            break
    else:
        print("No Arduino found on any port")
```

**connect_arduino_test.ino:**
```cpp
void setup() {
    Serial.begin(9600);
    pinMode(LED_BUILTIN, OUTPUT);
}

void loop() {
    if (Serial.available() > 0) {
        String received = Serial.readStringUntil('\n');
        
        // LED 토글
        digitalWrite(LED_BUILTIN, HIGH);
        delay(100);
        digitalWrite(LED_BUILTIN, LOW);
        
        // 에코 응답
        Serial.print("Echo: ");
        Serial.println(received);
    }
}
```

### 7-Segment Timer

**timer_final.ino (TM1637 라이브러리 사용):**
```cpp
#include <TM1637Display.h>

#define CLK 2
#define DIO 3

TM1637Display display(CLK, DIO);

unsigned long whiteTime = 600000;  // 10분 (밀리초)
unsigned long blackTime = 600000;
unsigned long lastUpdate = 0;
bool whiteActive = true;
bool paused = true;

void setup() {
    Serial.begin(9600);
    display.setBrightness(0x0f);  // 최대 밝기
    updateDisplay();
}

void loop() {
    // 시리얼 명령 수신
    if (Serial.available() > 0) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        
        if (command == "START") {
            paused = false;
            lastUpdate = millis();
        } else if (command == "PAUSE") {
            paused = true;
        } else if (command == "RESET") {
            whiteTime = 600000;
            blackTime = 600000;
            whiteActive = true;
            paused = true;
        } else if (command == "SWITCH") {
            whiteActive = !whiteActive;
            lastUpdate = millis();
        } else if (command.startsWith("SET:")) {
            // 시간 설정: "SET:300" (5분)
            int seconds = command.substring(4).toInt();
            whiteTime = seconds * 1000;
            blackTime = seconds * 1000;
        }
    }
    
    // 타이머 업데이트
    if (!paused) {
        unsigned long currentTime = millis();
        unsigned long elapsed = currentTime - lastUpdate;
        
        if (whiteActive) {
            whiteTime -= elapsed;
        } else {
            blackTime -= elapsed;
        }
        
        lastUpdate = currentTime;
        
        // 시간 초과 확인
        if (whiteTime <= 0 || blackTime <= 0) {
            paused = true;
            Serial.println("TIME_UP");
        }
    }
    
    updateDisplay();
    delay(100);  // 0.1초마다 업데이트
}

void updateDisplay() {
    unsigned long time = whiteActive ? whiteTime : blackTime;
    int minutes = time / 60000;
    int seconds = (time % 60000) / 1000;
    
    // MM:SS 형식
    int displayValue = minutes * 100 + seconds;
    display.showNumberDecEx(displayValue, 0b01000000, true);  // 콜론 표시
}
```

### Timer Control from Brain Module

**brain/timer/timer_manager.py:**
```python
import serial
import time

class TimerManager:
    def __init__(self, port='/dev/ttyACM0', baudrate=9600):
        self.ser = serial.Serial(port, baudrate, timeout=5)
        time.sleep(2)
    
    def start(self):
        self.ser.write(b"START\n")
        self.ser.flush()
    
    def pause(self):
        self.ser.write(b"PAUSE\n")
        self.ser.flush()
    
    def reset(self):
        self.ser.write(b"RESET\n")
        self.ser.flush()
    
    def switch_player(self):
        self.ser.write(b"SWITCH\n")
        self.ser.flush()
    
    def set_time(self, seconds):
        command = f"SET:{seconds}\n"
        self.ser.write(command.encode())
        self.ser.flush()
    
    def check_timeout(self):
        if self.ser.in_waiting > 0:
            response = self.ser.readline().decode().strip()
            if response == "TIME_UP":
                return True
        return False
    
    def close(self):
        self.ser.close()
```

## Testing Strategy

### Serial Connection Test

```bash
cd init/rasp-ardu
python connect_rasp.py
```

**예상 출력:**
```
Trying /dev/ttyUSB0...
Connected to /dev/ttyUSB0 at 9600 baud
Sent: HELLO
Received: Echo: HELLO
Success on /dev/ttyUSB0
```

### Timer Function Test

**시리얼 모니터에서 명령 전송:**
```
START    # 타이머 시작
PAUSE    # 일시정지
SWITCH   # 플레이어 전환
RESET    # 리셋
SET:300  # 5분으로 설정
```

### Integration Test

```python
# Python 스크립트로 타이머 제어
from brain.timer.timer_manager import TimerManager

timer = TimerManager(port='/dev/ttyACM0')
timer.set_time(300)  # 5분
timer.start()

# 플레이어 수 후 전환
timer.switch_player()

# 게임 종료 확인
if timer.check_timeout():
    print("Time is up!")

timer.close()
```

## Local Golden Rules

### Critical Do's

1. **포트 자동 감지**: /dev/ttyUSB0, /dev/ttyACM0 등 여러 포트 시도.
2. **초기화 대기**: Serial.begin() 후 2초 대기하여 아두이노 초기화 완료.
3. **버퍼 플러시**: 명령 전송 후 flush()로 즉시 전송 보장.
4. **타임아웃 설정**: 시리얼 읽기 시 타임아웃 5초 설정.
5. **에러 핸들링**: SerialException 처리로 포트 접근 오류 대응.

### Critical Don'ts

1. **절대 시리얼 포트 동시 접근 금지**: 여러 프로세스가 같은 포트 사용 시 충돌.
2. **초기화 대기 생략 금지**: Serial.begin() 후 즉시 통신 시 데이터 손실.
3. **무한 루프 블로킹 금지**: Serial.read() 대신 Serial.available() 확인.
4. **권한 오류 무시 금지**: sudo 또는 dialout 그룹 추가 필요.
5. **타이머 명령 검증 생략 금지**: 잘못된 명령으로 타이머 상태 오류 유발.

## File Structure & Naming

**주요 파일:**
- rasp-ardu/connect_rasp.py: 라즈베리파이 시리얼 테스트.
- rasp-ardu/connect_arduino_test/connect_arduino_test.ino: 아두이노 에코 테스트.
- timer/timer_final/timer_final.ino: 7세그먼트 타이머 메인 스케치.
- timer/7seg_test/7seg_test.ino: 디스플레이 테스트.
- head.stl: 타이머 하우징 3D 모델.

**함수 네이밍:**
- test_serial_connection(): 시리얼 연결 테스트.
- updateDisplay(): 7세그먼트 디스플레이 업데이트.
- switch_player(): 플레이어 전환.

## Operational Commands

### 시리얼 연결 테스트
```bash
cd init/rasp-ardu
python connect_rasp.py
```

### 아두이노 스케치 업로드
```bash
# Arduino IDE 열기
# 파일 -> 열기 -> init/timer/timer_final/timer_final.ino
# 도구 -> 보드 -> Arduino Uno
# 도구 -> 포트 -> /dev/ttyACM0
# 업로드
```

### 포트 권한 설정
```bash
sudo chmod 666 /dev/ttyUSB0
# 또는
sudo usermod -a -G dialout $USER
# 로그아웃 후 재로그인 필요
```

### TM1637 라이브러리 설치
```bash
# Arduino IDE:
# 스케치 -> 라이브러리 포함하기 -> 라이브러리 관리
# 검색: TM1637
# Grove - 4-Digit Display by Seeed Studio 설치
```

## Integration with Brain Module

**체스 게임 타이머 연동:**
```python
# brain/game/game_flow.py
from brain.timer.timer_manager import TimerManager

class ChessGame:
    def __init__(self):
        self.timer = TimerManager(port='/dev/ttyACM0')
        self.timer.set_time(600)  # 10분
    
    def start_game(self):
        self.timer.start()
    
    def make_move(self, move):
        # 수 적용
        self.board.push(move)
        
        # 플레이어 전환
        self.timer.switch_player()
        
        # 타임아웃 확인
        if self.timer.check_timeout():
            print("Game over: Time out")
            return False
        
        return True
```

## Troubleshooting

**포트 접근 권한 오류:**
```bash
# 오류: Permission denied: '/dev/ttyUSB0'
sudo chmod 666 /dev/ttyUSB0

# 영구 해결
sudo usermod -a -G dialout $USER
# 재로그인
```

**아두이노를 찾을 수 없음:**
```bash
# USB 연결 확인
lsusb

# 시리얼 포트 확인
ls /dev/tty*

# 아두이노 보드 확인
# Uno: /dev/ttyACM0
# CH340 칩: /dev/ttyUSB0
```

**TM1637 디스플레이 작동 안 함:**
```
# 전원 확인: 5V VCC, GND 연결.
# 배선 확인: CLK = Pin 2, DIO = Pin 3.
# 라이브러리 확인: TM1637Display 설치.
# 밝기 조절: setBrightness(0x0f).
```

**타이머 시간 표시 오류:**
```cpp
// 디버깅 출력 추가
void updateDisplay() {
    unsigned long time = whiteActive ? whiteTime : blackTime;
    int minutes = time / 60000;
    int seconds = (time % 60000) / 1000;
    
    Serial.print("Minutes: ");
    Serial.print(minutes);
    Serial.print(" Seconds: ");
    Serial.println(seconds);
    
    int displayValue = minutes * 100 + seconds;
    display.showNumberDecEx(displayValue, 0b01000000, true);
}
```

## 3D Printing Head Housing

**head.stl 사용법:**
```
# 3D 프린팅 설정
- 재료: PLA 또는 PETG.
- 레이어 높이: 0.2mm.
- 인필: 20%.
- 서포트: 필요 시 사용.
- 베드 온도: 60도 (PLA).
```

## Performance Optimization

1. **타이머 정확도**: millis() 오버플로우 처리 (49일 후).
   ```cpp
   unsigned long elapsed = currentTime - lastUpdate;
   // currentTime < lastUpdate인 경우 오버플로우 발생
   if (currentTime < lastUpdate) {
       elapsed = (0xFFFFFFFF - lastUpdate) + currentTime;
   }
   ```

2. **디스플레이 플리커 방지**: 매 프레임 업데이트 대신 변경 시만 업데이트.
   ```cpp
   static int lastDisplayValue = -1;
   if (displayValue != lastDisplayValue) {
       display.showNumberDecEx(displayValue, 0b01000000, true);
       lastDisplayValue = displayValue;
   }
   ```
