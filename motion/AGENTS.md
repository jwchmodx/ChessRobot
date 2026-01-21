# Motion Module: Robot Arm Inverse Kinematics

Arduino 기반 로봇 암 제어 시스템. 역기구학 계산 및 서보 모터 제어를 담당.

## Module Context

Motion 모듈은 ChessRobot의 물리적 동작을 제어하며 다음 기능 제공:

**역기구학 (IK)**: 목표 좌표 (X, Y, Z)를 관절 각도로 변환.
**정기구학 (FK)**: 관절 각도에서 엔드 이펙터 위치 계산 (검증 용도).
**모터 제어**: 서보 모터 PWM 신호 생성 및 각도 설정.
**시리얼 통신**: 라즈베리파이로부터 좌표 수신 및 응답 전송.

## Tech Stack & Constraints

### Hardware Components

**서보 모터:**
- Base (회전): 0-180도.
- Shoulder (상완): 0-180도.
- Elbow (전완): 0-180도.
- Wrist (손목): 0-180도 (옵션).
- Gripper (집게): 0-90도.

**아두이노:**
- Arduino Uno / Mega 2560.
- PWM 핀: 6개 (각 서보마다 1개).

**전원:**
- 서보 모터 전용 5V/6V 전원 공급 (최소 3A).
- 아두이노와 전원 GND 공유 필수.

### Serial Communication Protocol

**Baud Rate:** 9600.

**명령 포맷 (라즈베리파이 -> 아두이노):**
```
X,Y,Z\n
```
예: `150.5,200.0,50.0\n`

**응답 포맷 (아두이노 -> 라즈베리파이):**
```
OK\n         # 성공
ERROR:msg\n  # 실패 (에러 메시지 포함)
```

### Kinematic Constraints

**작업 영역 (Workspace):**
- X: -300mm ~ 300mm.
- Y: 0mm ~ 400mm.
- Z: 0mm ~ 300mm.

**관절 각도 제약:**
- Base: 0-180도.
- Shoulder: 30-150도 (물리적 충돌 방지).
- Elbow: 30-150도.

**로봇 암 길이 (예시):**
- L1 (Base to Shoulder): 100mm.
- L2 (Shoulder to Elbow): 150mm.
- L3 (Elbow to Wrist): 120mm.

## Implementation Patterns

### RobotArmIK Class

**RobotArmIK.h:**
```cpp
#ifndef ROBOT_ARM_IK_H
#define ROBOT_ARM_IK_H

#include <Arduino.h>
#include <math.h>

class RobotArmIK {
public:
    RobotArmIK(float l1, float l2, float l3);
    
    // 역기구학: (x, y, z) -> (theta1, theta2, theta3)
    bool calculateIK(float x, float y, float z, float* angles);
    
    // 정기구학: (theta1, theta2, theta3) -> (x, y, z)
    void calculateFK(float theta1, float theta2, float theta3, float* position);
    
    // 관절 각도 제약 검증
    bool validateAngles(float theta1, float theta2, float theta3);
    
private:
    float L1, L2, L3;  // 링크 길이
    
    const float THETA1_MIN = 0.0;
    const float THETA1_MAX = 180.0;
    const float THETA2_MIN = 30.0;
    const float THETA2_MAX = 150.0;
    const float THETA3_MIN = 30.0;
    const float THETA3_MAX = 150.0;
};

#endif
```

**RobotArmIK.cpp:**
```cpp
#include "RobotArmIK.h"

RobotArmIK::RobotArmIK(float l1, float l2, float l3) {
    L1 = l1;
    L2 = l2;
    L3 = l3;
}

bool RobotArmIK::calculateIK(float x, float y, float z, float* angles) {
    // Base 각도 (회전)
    float theta1 = atan2(y, x) * 180.0 / PI;
    
    // 평면 거리
    float r = sqrt(x * x + y * y);
    
    // Shoulder와 Elbow 각도 (2D IK)
    float d = sqrt(r * r + (z - L1) * (z - L1));
    
    // 코사인 법칙
    float cos_theta3 = (d * d - L2 * L2 - L3 * L3) / (2 * L2 * L3);
    
    // 도달 불가능한 위치 확인
    if (cos_theta3 < -1.0 || cos_theta3 > 1.0) {
        return false;
    }
    
    float theta3 = acos(cos_theta3) * 180.0 / PI;
    
    float alpha = atan2(z - L1, r) * 180.0 / PI;
    float beta = atan2(L3 * sin(theta3 * PI / 180.0), L2 + L3 * cos(theta3 * PI / 180.0)) * 180.0 / PI;
    float theta2 = alpha + beta;
    
    // 각도 검증
    if (!validateAngles(theta1, theta2, theta3)) {
        return false;
    }
    
    // 결과 저장
    angles[0] = theta1;
    angles[1] = theta2;
    angles[2] = theta3;
    
    return true;
}

void RobotArmIK::calculateFK(float theta1, float theta2, float theta3, float* position) {
    float t1_rad = theta1 * PI / 180.0;
    float t2_rad = theta2 * PI / 180.0;
    float t3_rad = theta3 * PI / 180.0;
    
    // X, Y, Z 계산
    float r = L2 * cos(t2_rad) + L3 * cos(t2_rad + t3_rad);
    
    position[0] = r * cos(t1_rad);  // X
    position[1] = r * sin(t1_rad);  // Y
    position[2] = L1 + L2 * sin(t2_rad) + L3 * sin(t2_rad + t3_rad);  // Z
}

bool RobotArmIK::validateAngles(float theta1, float theta2, float theta3) {
    if (theta1 < THETA1_MIN || theta1 > THETA1_MAX) return false;
    if (theta2 < THETA2_MIN || theta2 > THETA2_MAX) return false;
    if (theta3 < THETA3_MIN || theta3 > THETA3_MAX) return false;
    return true;
}
```

### Arduino Main Sketch

**IKtest_coordinates.ino:**
```cpp
#include <Servo.h>
#include "RobotArmIK.h"

// 서보 모터 선언
Servo baseServo;
Servo shoulderServo;
Servo elbowServo;
Servo gripperServo;

// IK 계산기
RobotArmIK ik(100.0, 150.0, 120.0);  // L1, L2, L3

void setup() {
    Serial.begin(9600);
    
    // 서보 핀 연결
    baseServo.attach(3);
    shoulderServo.attach(5);
    elbowServo.attach(6);
    gripperServo.attach(9);
    
    // 초기 위치
    baseServo.write(90);
    shoulderServo.write(90);
    elbowServo.write(90);
    gripperServo.write(45);
    
    Serial.println("Ready");
}

void loop() {
    if (Serial.available() > 0) {
        // 좌표 수신: "X,Y,Z\n"
        String input = Serial.readStringUntil('\n');
        
        float x, y, z;
        if (parseCoordinates(input, &x, &y, &z)) {
            float angles[3];
            
            if (ik.calculateIK(x, y, z, angles)) {
                // 서보 각도 설정
                baseServo.write((int)angles[0]);
                shoulderServo.write((int)angles[1]);
                elbowServo.write((int)angles[2]);
                
                Serial.println("OK");
            } else {
                Serial.println("ERROR:IK failed");
            }
        } else {
            Serial.println("ERROR:Invalid format");
        }
    }
}

bool parseCoordinates(String input, float* x, float* y, float* z) {
    int firstComma = input.indexOf(',');
    int secondComma = input.indexOf(',', firstComma + 1);
    
    if (firstComma == -1 || secondComma == -1) {
        return false;
    }
    
    *x = input.substring(0, firstComma).toFloat();
    *y = input.substring(firstComma + 1, secondComma).toFloat();
    *z = input.substring(secondComma + 1).toFloat();
    
    return true;
}
```

## Testing Strategy

### IK Calculation Test

**coordinate_test.ino:**
```cpp
void testIK() {
    float test_coords[][3] = {
        {200.0, 100.0, 50.0},
        {150.0, 150.0, 100.0},
        {100.0, 200.0, 80.0}
    };
    
    for (int i = 0; i < 3; i++) {
        float angles[3];
        float x = test_coords[i][0];
        float y = test_coords[i][1];
        float z = test_coords[i][2];
        
        if (ik.calculateIK(x, y, z, angles)) {
            Serial.print("Target: (");
            Serial.print(x); Serial.print(", ");
            Serial.print(y); Serial.print(", ");
            Serial.print(z); Serial.println(")");
            
            Serial.print("Angles: (");
            Serial.print(angles[0]); Serial.print(", ");
            Serial.print(angles[1]); Serial.print(", ");
            Serial.print(angles[2]); Serial.println(")");
            
            // FK로 검증
            float position[3];
            ik.calculateFK(angles[0], angles[1], angles[2], position);
            
            Serial.print("Verified: (");
            Serial.print(position[0]); Serial.print(", ");
            Serial.print(position[1]); Serial.print(", ");
            Serial.print(position[2]); Serial.println(")");
            Serial.println();
        } else {
            Serial.println("IK failed");
        }
    }
}
```

### Motor Angle Test

**motor_angle_test.ino:**
```cpp
void testMotors() {
    Serial.println("Testing Base Servo (0-180)");
    for (int angle = 0; angle <= 180; angle += 30) {
        baseServo.write(angle);
        delay(500);
    }
    
    Serial.println("Testing Shoulder Servo (30-150)");
    for (int angle = 30; angle <= 150; angle += 30) {
        shoulderServo.write(angle);
        delay(500);
    }
}
```

### Serial Communication Test

**Python 테스트 스크립트:**
```python
import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=5)
time.sleep(2)  # Arduino 초기화 대기

# 좌표 전송
commands = [
    "200.0,100.0,50.0\n",
    "150.0,150.0,100.0\n",
    "100.0,200.0,80.0\n"
]

for cmd in commands:
    ser.write(cmd.encode())
    response = ser.readline().decode().strip()
    print(f"Sent: {cmd.strip()} | Response: {response}")
    time.sleep(1)

ser.close()
```

## Local Golden Rules

### Critical Do's

1. **전원 분리**: 서보 모터 전원은 아두이노와 별도로 공급. GND만 공유.
2. **각도 범위 검증**: IK 계산 전후로 관절 각도가 제약 범위 내인지 확인.
3. **FK 검증**: IK 계산 후 FK로 역계산하여 오차 1mm 이내 확인.
4. **부드러운 동작**: 급격한 각도 변화는 서보 손상 유발. 점진적 이동 구현.
5. **시리얼 버퍼 클리어**: 새 명령 수신 전 버퍼를 비워 오래된 데이터 방지.

### Critical Don'ts

1. **절대 관절 제약 무시 금지**: 물리적 충돌로 서보 또는 구조물 파손.
2. **시리얼 통신 블로킹 금지**: Serial.read() 대신 Serial.available() 확인 후 읽기.
3. **부하 과다 금지**: 서보 모터 스펙 초과 하중 부착 금지.
4. **PWM 핀 오용 금지**: 서보는 반드시 PWM 지원 핀에 연결.
5. **정기구학 생략 금지**: IK 결과를 항상 FK로 검증하여 신뢰성 확보.

## File Structure & Naming

**주요 파일:**
- IKtest/IKtest_coordinates/IKtest_coordinates.ino: 메인 스케치.
- RobotArmIK.cpp: 역기구학 라이브러리 구현.
- RobotArmIK.h: 역기구학 라이브러리 헤더.
- motor_angle_test/motor_angle_test.ino: 모터 각도 테스트.
- coordinate_test.ino: IK 계산 검증.

**클래스 네이밍:**
- RobotArmIK: 역기구학 계산 클래스.

**함수 네이밍:**
- calculateIK(): 역기구학 계산.
- calculateFK(): 정기구학 계산.
- validateAngles(): 각도 범위 검증.
- parseCoordinates(): 시리얼 문자열 파싱.

## Operational Commands

### Arduino IDE 업로드

```bash
# Arduino IDE 열기
# 파일 -> 열기 -> motion/IKtest/IKtest_coordinates/IKtest_coordinates.ino
# 도구 -> 보드 -> Arduino Uno (또는 Mega)
# 도구 -> 포트 -> /dev/ttyUSB0 (또는 COM3)
# 업로드 버튼 클릭
```

### 시리얼 모니터 테스트

```bash
# Arduino IDE에서 시리얼 모니터 열기 (Ctrl+Shift+M)
# Baud rate: 9600
# 명령 입력: 200.0,100.0,50.0
```

### Python 시리얼 통신

```bash
cd init/rasp-ardu
python connect_rasp.py
```

## Integration with Brain Module

**Brain 모듈에서 좌표 전송:**
```python
# brain/robot_arm/robot_arm_controller.py
import serial
import time

class RobotArmController:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        self.ser = serial.Serial(port, baudrate, timeout=5)
        time.sleep(2)  # Arduino 초기화 대기
    
    def move_to(self, x, y, z):
        command = f"{x},{y},{z}\n"
        self.ser.write(command.encode())
        self.ser.flush()
        
        response = self.ser.readline().decode().strip()
        
        if response == "OK":
            return True
        else:
            print(f"Error: {response}")
            return False
    
    def close(self):
        self.ser.close()
```

## Performance Optimization

1. **이동 속도 제어**: 각도 차이에 비례한 딜레이 추가.
   ```cpp
   void smoothMove(Servo& servo, int target_angle, int current_angle) {
       int step = (target_angle > current_angle) ? 1 : -1;
       for (int angle = current_angle; angle != target_angle; angle += step) {
           servo.write(angle);
           delay(15);  # 15ms per degree
       }
   }
   ```

2. **궤적 계획**: 시작점에서 목표점까지 직선 궤적 생성.
   ```cpp
   void moveLinear(float x1, float y1, float z1, float x2, float y2, float z2, int steps) {
       for (int i = 0; i <= steps; i++) {
           float t = (float)i / steps;
           float x = x1 + t * (x2 - x1);
           float y = y1 + t * (y2 - y1);
           float z = z1 + t * (z2 - z1);
           
           float angles[3];
           if (ik.calculateIK(x, y, z, angles)) {
               baseServo.write(angles[0]);
               shoulderServo.write(angles[1]);
               elbowServo.write(angles[2]);
               delay(50);
           }
       }
   }
   ```

## Troubleshooting

**서보 모터 작동 안 함:**
```
# 전원 확인: 5V 3A 이상 공급.
# PWM 핀 확인: 3, 5, 6, 9, 10, 11 (Uno 기준).
# GND 공유 확인: 아두이노와 서보 전원 GND 연결.
```

**IK 계산 실패:**
```
# 목표 좌표가 작업 영역 밖인 경우.
# 로봇 암 길이 (L1, L2, L3) 확인.
# 관절 각도 제약 범위 조정.
```

**시리얼 통신 오류:**
```bash
# 포트 권한 확인
sudo chmod 666 /dev/ttyUSB0

# Baud rate 일치 확인
# 아두이노: Serial.begin(9600)
# Python: serial.Serial(..., 9600)
```

**서보 떨림 현상:**
```
# 전원 부족: 전류 용량 증가.
# 부하 과다: 기물 무게 확인.
# PWM 신호 노이즈: 전원 필터 캐패시터 추가.
```
