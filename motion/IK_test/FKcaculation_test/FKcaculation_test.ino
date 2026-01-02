#include <Arduino.h>

const float L1 = 10.0;  // 첫 번째 링크 길이
const float L2 = 10.0;  // 두 번째 링크 길이

// Forward Kinematics
void forwardKinematics(float t1, float t2, float t3, float &x, float &y, float &z) {
  // 라디안 단위로 계산
  float d = L1 * cos(t2) + L2 * cos(t2 + t3);
  x = d * cos(t1);
  y = d * sin(t1);
  z = L1 * sin(t2) + L2 * sin(t2 + t3);
}

void setup() {
  Serial.begin(9600);
  Serial.println("Forward Kinematics Test Ready!");
}

void loop() {
  if (Serial.available() >= 3) {  // 적어도 3개의 float 입력이 들어올 때
    float t1 = Serial.parseFloat();
    float t2 = Serial.parseFloat();
    float t3 = Serial.parseFloat();

    // Forward Kinematics
    float x, y, z;
    forwardKinematics(radians(t1), radians(t2), radians(t3), x, y, z);

    Serial.print("Input angles -> Shoulder: "); Serial.print(t1);
    Serial.print(" LowerArm: "); Serial.print(t2);
    Serial.print(" UpperArm: "); Serial.println(t3);

    Serial.print("Calculated position -> X: "); Serial.print(x);
    Serial.print("  Y: "); Serial.print(y);
    Serial.print("  Z: "); Serial.println(z);
  }
}
