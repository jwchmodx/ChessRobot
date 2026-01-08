#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include "RobotArmIK.h"

// PCA9685 서보 드라이버 객체
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// 로봇팔 객체 생성 (채널 번호는 하드웨어 연결에 맞게 수정)
RobotArmIK arm(&pwm, 0, 1, 2, 3, 10.0, 10.0);
// 링크 길이 (cm 단위, 실제 로봇팔에 맞게 수정)

String inputString = "";   // 시리얼 입력 버퍼
bool stringComplete = false;

void setup() {
  Serial.begin(9600);
  pwm.begin();
  pwm.setPWMFreq(60);

  Serial.println("로봇팔 IK 테스트 시작");
  Serial.println("좌표를 입력하세요. 형식: x,y,z (예: 10,5,5)");
}

void loop() {
  // 시리얼 입력이 완료되면 처리
  if (stringComplete) {
    processInput(inputString);
    inputString = "";
    stringComplete = false;
  }
}

// ---- 시리얼 데이터 읽기 ----
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == '\n') {     // 엔터(개행) 입력 시 종료
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}

// ---- 입력된 문자열 처리 ----
void processInput(String data) {
  data.trim();
  if (data.length() == 0) return;

  // 콤마로 분리
  int firstComma = data.indexOf(',');
  int secondComma = data.indexOf(',', firstComma + 1);

  if (firstComma < 0 || secondComma < 0) {
    Serial.println("⚠️ 입력 형식 오류. 예: 10,5,5");
    return;
  }

  float x = data.substring(0, firstComma).toFloat();
  float y = data.substring(firstComma + 1, secondComma).toFloat();
  float z = data.substring(secondComma + 1).toFloat();

  Serial.print("목표 좌표: (");
  Serial.print(x); Serial.print(", ");
  Serial.print(y); Serial.print(", ");
  Serial.print(z); Serial.println(")");

  printIKAngles(x, y, z);
}

// ---- IK 계산 후 각도 출력 ----
void printIKAngles(float x, float y, float z) {
  float theta_shoulder_rad = atan2(y, x);
  float d = sqrt(pow(x, 2) + pow(y, 2));

  float distance = sqrt(pow(d, 2) + pow(z, 2));
  if (distance > arm.L1 + arm.L2) {
    Serial.println("⚠️ 도달할 수 없는 거리");
    return;
  }

  float cos_theta2 = (pow(d, 2) + pow(z, 2) - pow(arm.L1, 2) - pow(arm.L2, 2)) / (2 * arm.L1 * arm.L2);
  float theta_lower_rad = -acos(cos_theta2);

  float k1 = arm.L1 + arm.L2 * cos(theta_lower_rad);
  float k2 = arm.L2 * sin(theta_lower_rad);
  float theta_upper_rad = atan2(z, d) - atan2(k2, k1);

  float theta_shoulder_deg = theta_shoulder_rad * 180.0 / M_PI;
  float theta_upper_deg = theta_upper_rad * 180.0 / M_PI;
  float theta_lower_deg = theta_lower_rad * 180.0 / M_PI;

  // 서보 적용 각도 (보정 포함)
  float shoulder_angle = constrain(90 + theta_shoulder_deg, 0, 180);
  float upper_angle    = constrain(180 - theta_upper_deg, 0, 180);
  float lower_angle    = constrain(180 + theta_lower_deg, 0, 180);

  // 출력
  Serial.print("계산된 각도 (deg) → ");
  Serial.print("Shoulder: "); Serial.print(theta_shoulder_deg, 2);
  Serial.print(", Upper: ");  Serial.print(theta_upper_deg, 2);
  Serial.print(", Lower: ");  Serial.print(theta_lower_deg, 2);
  Serial.println();

  Serial.print("서보 적용 각도 (deg) → ");
  Serial.print("Shoulder: "); Serial.print(shoulder_angle, 2);
  Serial.print(", Upper: ");  Serial.print(upper_angle, 2);
  Serial.print(", Lower: ");  Serial.print(lower_angle, 2);
  Serial.println("\n-------------------");
}
