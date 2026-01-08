// #include <Wire.h>
// #include <Adafruit_PWMServoDriver.h>
// #include "RobotArmIK.h"

// #define NUM_SERVOS 4

// // PCA9685 객체
// Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

// // 서보 채널 지정
// uint8_t CH_SHOULDER = 0;
// uint8_t CH_UPPER    = 1;
// uint8_t CH_LOWER    = 2;
// uint8_t CH_GRIP     = 3;

// // 로봇팔 링크 길이 (mm 단위 추천)
// float L1 = 300.0;   // 상박
// float L2 = 350.0;   // 하박

// // 서보별 펄스 범위 (캘리브레이션 값!)
// int servoMins[NUM_SERVOS] = {85, 90, 75, 210};
// int servoMaxs[NUM_SERVOS] = {455, 436, 445, 230};

// // RobotArmIK 객체 생성
// RobotArmIK arm(
//   &pwm,
//   CH_SHOULDER,
//   CH_UPPER,
//   CH_LOWER,
//   CH_GRIP,
//   L1,
//   L2,
//   servoMins,
//   servoMaxs
// );

// // ------------------------------

// void setup() {
//   Serial.begin(115200);
//   Wire.begin();

//   pwm.begin();
//   pwm.setPWMFreq(50);   // 서보용 주파수

//   delay(500);

//   Serial.println("=== Robot Arm Serial Control Ready ===");
//   Serial.println("Input format: x y z");
//   Serial.println("Example: 120 30 50");
// }

// void loop() {
//   if (Serial.available()) {
//     String line = Serial.readStringUntil('\n');
//     line.trim();

//     if (line.length() == 0) return;

//     float x, y, z;

//     // 입력 파싱
//     int count = sscanf(line.c_str(), "%f %f %f", &x, &y, &z);

//     if (count == 3) {
//       Serial.print("Moving to → x:");
//       Serial.print(x);
//       Serial.print(" y:");
//       Serial.print(y);
//       Serial.print(" z:");
//       Serial.println(z);

//       arm.moveTo(x, y, z);
//     } else {
//       Serial.println("❌ Invalid input. Use: x y z");
//     }
//   }
// }