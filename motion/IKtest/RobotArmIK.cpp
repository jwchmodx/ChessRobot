#include "RobotArmIK.h"
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

#define NUM_SERVOS 3  // 사용하는 모터 개수 (어깨, 상박, 하박, 그리퍼)

// =============================
// 그리퍼용 DC 모터(TB6612 등) 제어 핀 - motor_test.ino와 동일하게 사용
// =============================
const int GRIP_STBY = 10; // standby
const int GRIP_PWMA = 3;  // Speed control 
const int GRIP_AIN1 = 9;  // Direction
const int GRIP_AIN2 = 8;  // Direction

// 간단한 그리퍼 모터 제어 함수 (motor_test.ino 방식)
static void gripMotorInitPins() {
  pinMode(GRIP_STBY, OUTPUT);
  pinMode(GRIP_PWMA, OUTPUT);
  pinMode(GRIP_AIN1, OUTPUT);
  pinMode(GRIP_AIN2, OUTPUT);
}

static void gripMotorMove(int speed, int direction) {
  // direction: 0 clockwise, 1 counter-clockwise
  // speed: 0~255
  digitalWrite(GRIP_STBY, HIGH); // disable standby

  bool inPin1 = LOW;
  bool inPin2 = HIGH;

  if (direction == 1) {
    inPin1 = HIGH;
    inPin2 = LOW;
  }

  digitalWrite(GRIP_AIN1, inPin1);
  digitalWrite(GRIP_AIN2, inPin2);
  analogWrite(GRIP_PWMA, speed);
}

static void gripMotorStop() {
  // enable standby  
  digitalWrite(GRIP_STBY, LOW); 
}

// 생성자: 드라이버 객체 포인터와 각 서보의 '채널 번호'와 서보별 min/max 값을 입력받습니다.
RobotArmIK::RobotArmIK(Adafruit_PWMServoDriver* pwm,
                     uint8_t channel_shoulder, uint8_t channel_upper,
                     uint8_t channel_lower, uint8_t channel_grip,
                     float L1, float L2,
                     int servoMins[NUM_SERVOS], int servoMaxs[NUM_SERVOS]) {
  this->pwm = pwm;
  this->channel_shoulder = channel_shoulder;
  this->channel_upper = channel_upper;
  this->channel_lower = channel_lower;
  this->channel_grip = channel_grip;
  this->L1 = L1;
  this->L2 = L2;

   // [추가] 배열 복사
  for (int i = 0; i < NUM_SERVOS; i++) {
    this->servoMins[i] = servoMins[i];
    this->servoMaxs[i] = servoMaxs[i];
  }
}



  

void RobotArmIK::begin() {
  // 서보 드라이버 초기화는 .ino 쪽에서 하고,
  // 여기서는 그리퍼 DC 모터용 핀만 세팅
  gripMotorInitPins();
}




// 각도를 펄스로 변환 (채널별 개별 min/max 적용)
float RobotArmIK::angleToPulse(uint8_t channel, float angle) {
  int idx = 0;

  // 채널 번호에 따라 배열 인덱스 결정
  if (channel == channel_shoulder) idx = 0;
  else if (channel == channel_upper) idx = 1;
  else if (channel == channel_lower) idx = 2;
  else if (channel == channel_grip) idx = 3;

  return map(angle, 0, 180, servoMins[idx], servoMaxs[idx]);
}

void RobotArmIK::moveTo(float x, float y, float z) {
  float theta_shoulder_rad = atan2(y, x);
  float d = sqrt(pow(x, 2) + pow(y, 2));

  float distance = sqrt(pow(d, 2) + pow(z, 2));
  if (distance > L1 + L2) {
    Serial.println("도달할 수 없는 거리");
    return;
  }

  float cos_theta2 = (pow(L1, 2) + pow(L2, 2) - pow(d, 2) - pow(z, 2)) / (2 * L1 * L2);
  float theta_lower_rad = acos(cos_theta2);

  float k1 = L1 + L2 * cos(M_PI-theta_lower_rad);
  float k2 = L2 * sin(M_PI-theta_lower_rad);
  float theta_upper_rad = M_PI - atan2(z, d) - atan2(k2, k1); // theta 값 연산 실수 수정

  float theta_shoulder_deg = theta_shoulder_rad * 180.0 / M_PI;
  float theta_upper_deg    = theta_upper_rad    * 180.0 / M_PI;
  float theta_lower_deg    = theta_lower_rad    * 180.0 / M_PI;

  // [중요] 실제 기구 한계에 맞춰 각도 범위를 조금 좁게 제한
  float shoulder_angle = constrain(theta_shoulder_deg,  0, 180);
  float upper_angle    = constrain(theta_upper_deg,    0, 180);
  float lower_angle    = constrain(theta_lower_deg,    0, 180);

  // ============================================================
  // 방법 선택 (아래 중 하나만 사용)
  // ============================================================
  
  // ========== 방법 1: 직접 이동 (가장 부드럽고 빠름, 추천!) ==========
  // 서보가 자체적으로 부드럽게 이동하므로 보간 불필요
  // int pwm_shoulder = angleToPulse(channel_shoulder, shoulder_angle);
  // int pwm_upper    = angleToPulse(channel_upper,    upper_angle);
  // int pwm_lower    = angleToPulse(channel_lower,    lower_angle);
  
  // pwm->setPWM(channel_shoulder, 0, pwm_shoulder);
  // pwm->setPWM(channel_upper,    0, pwm_upper);
  // pwm->setPWM(channel_lower,    0, pwm_lower);
  
  // 서보가 이동할 시간만 대기 (조정 가능)

  
  // ========== 방법 2: 단순 보간 (보간이 꼭 필요하면) ==========
  static float cur_shoulder = 90.0;
  static float cur_upper    = 90.0;
  static float cur_lower    = 90.0;
  static bool  initialized  = false;

  if (!initialized) {
    cur_shoulder = shoulder_angle;
    cur_upper    = upper_angle;
    cur_lower    = lower_angle;
    initialized  = true;
  }

  const int   STEPS      = 60;   // 단계 수 줄임 (60 → 10)
  const int   STEP_DELAY = 20;   // delay 늘림 (20 → 50ms)

  for (int i = 1; i <= STEPS; i++) {
    float t = (float)i / (float)STEPS;  // linear 보간 (0~1)

    float step_shoulder = cur_shoulder + (shoulder_angle - cur_shoulder) * t;
    float step_upper    = cur_upper    + (upper_angle    - cur_upper)    * t;
    float step_lower    = cur_lower    + (lower_angle    - cur_lower)    * t;

    int pwm_shoulder = angleToPulse(channel_shoulder, step_shoulder);
    int pwm_upper    = angleToPulse(channel_upper,    step_upper);
    int pwm_lower    = angleToPulse(channel_lower,    step_lower);

    pwm->setPWM(channel_shoulder, 0, pwm_shoulder);
    pwm->setPWM(channel_upper,    0, pwm_upper);
    pwm->setPWM(channel_lower,    0, pwm_lower);
    
    delay(STEP_DELAY);
  }

  cur_shoulder = shoulder_angle;
  cur_upper    = upper_angle;
  cur_lower    = lower_angle;
  

  // 최종 위치 로그
  Serial.print("[moveTo] x: "); Serial.print(x);
  Serial.print(", y: "); Serial.print(y);
  Serial.print(", z: "); Serial.print(z);
  Serial.print(" | shoulder: "); Serial.print(shoulder_angle);
  Serial.print(", upper: "); Serial.print(upper_angle);
  Serial.print(", lower: "); Serial.println(lower_angle);
}

void RobotArmIK::gripOpen() {
  // motor_test.ino 테스트 기준: PWM 110일 때 "열림"
  // direction 값은 실제 동작을 보고 0/1 바꿔서 사용하면 됨
  int speed = 185;
  int direction = 0; // 필요 시 0과 1을 바꿔서 테스트

  gripMotorMove(speed, direction);
  delay(500);        // 모터를 일정 시간 구동 (필요에 따라 조정)
  gripMotorStop();
}

void RobotArmIK::gripClose() {
  // motor_test.ino 테스트 기준: PWM 155일 때 "닫힘"
  int speed = 185;
  int direction = 1; // 열기와 반대 방향

  gripMotorMove(speed, direction);
  delay(500);        // 모터를 일정 시간 구동 (필요에 따라 조정)
  gripMotorStop();
}
