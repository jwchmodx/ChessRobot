// // #include <Wire.h>
// // #include <Adafruit_PWMServoDriver.h>

// // #define GRIP_CHANNEL 4

// // // 서보 드라이버 객체 생성
// // Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// // void setup() {
// //   Serial.begin(9600);
  
// //   // 서보 드라이버 초기화
// //   pwm.begin();
// //   pwm.setOscillatorFrequency(27000000);
// //   pwm.setPWMFreq(50); // 서보 모터는 50Hz
  
// //   Serial.println("그리퍼 PWM 테스트 시작");
// //   Serial.println("숫자를 입력하면 그 PWM값으로 그리퍼가 움직입니다 (예: 210, 230 등)");
// //   Serial.println("범위: 210~230 (또는 servoMaxs/servoMins 값)");
// // }

// // void loop() {
// //   if (Serial.available()) {
// //     String input = Serial.readStringUntil('\n');
// //     input.trim();
    
// //     // 입력값이 숫자인지 확인
// //     if (input.length() > 0 && isNumeric(input)) {
// //       int pwmValue = input.toInt();
      
// //       Serial.print("그리퍼 PWM값 설정: ");
// //       Serial.println(pwmValue);
      
// //       // PWM값 설정
// //       pwm.setPWM(GRIP_CHANNEL, 0, pwmValue);
      
// //       delay(500);
// //     } else {
// //       Serial.println("숫자를 입력해주세요!");
// //     }
// //   }
// // }

// // // 문자열이 모두 숫자인지 확인하는 함수
// // bool isNumeric(String str) {
// //   for (int i = 0; i < str.length(); i++) {
// //     if (!isDigit(str.charAt(i))) {
// //       return false;
// //     }
// //   }
// //   return true;
// // }


// int STBY = 10; //standby

// //Motor A
// int PWMA = 3; //Speed control 
// int AIN1 = 9; //Direction
// int AIN2 = 8; //Direction

// // 서보 모터처럼 제어하기 위한 변수들
// int currentAngle = 0;  // 현재 각도 (0~180도)
// int maxAngle = 180;    // 최대 각도 제한
// int minAngle = 0;      // 최소 각도 제한

// // 각도당 이동 시간 (밀리초) - 모터 특성에 따라 조정 필요
// // 예: 1도당 10ms면 180도 이동에 1.8초
// float msPerDegree = 10.0;  // 이 값은 실제 모터에 맞게 조정하세요

// void setup(){
//   Serial.begin(9600);
  
//   pinMode(STBY, OUTPUT);
//   pinMode(PWMA, OUTPUT);
//   pinMode(AIN1, OUTPUT);
//   pinMode(AIN2, OUTPUT);

//   Serial.println("서보 모터 스타일 DC 모터 제어");
//   Serial.println("명령어:");
//   Serial.println("  PWM값 입력: 0~255 (예: 128)");
//   Serial.println("  각도 입력: a0~a180 (예: a90)");
//   Serial.println("  각도 제한 설정: min0~180 max0~180 (예: min0 max180)");
//   Serial.println("  현재 상태 확인: s");
// }

// void loop(){
//   if (Serial.available()) {
//     String input = Serial.readStringUntil('\n');
//     input.trim();
    
//     // 각도 명령 (a0~a180)
//     if (input.startsWith("a") || input.startsWith("A")) {
//       String angleStr = input.substring(1);
//       if (isNumeric(angleStr)) {
//         int targetAngle = angleStr.toInt();
//         moveToAngle(targetAngle, 128); // 기본 속도 128
//       }
//     }
//     // 각도 제한 설정 (min0 max180)
//     else if (input.startsWith("min")) {
//       String minStr = input.substring(3);
//       if (isNumeric(minStr)) {
//         minAngle = minStr.toInt();
//         Serial.print("최소 각도 설정: ");
//         Serial.println(minAngle);
//       }
//     }
//     else if (input.startsWith("max")) {
//       String maxStr = input.substring(3);
//       if (isNumeric(maxStr)) {
//         maxAngle = maxStr.toInt();
//         Serial.print("최대 각도 설정: ");
//         Serial.println(maxAngle);
//       }
//     }
//     // 상태 확인
//     else if (input == "s" || input == "S") {
//       Serial.print("현재 각도: ");
//       Serial.print(currentAngle);
//       Serial.print("도, 제한 범위: ");
//       Serial.print(minAngle);
//       Serial.print("~");
//       Serial.println(maxAngle);
//     }
//     // PWM 값 직접 입력 (0~255)
//     else if (isNumeric(input)) {
//       int pwmValue = input.toInt();
//       if (pwmValue >= 0 && pwmValue <= 255) {
//         Serial.print("PWM 값 설정: ");
//         Serial.println(pwmValue);
//         setPWM(pwmValue);
//       } else {
//         Serial.println("PWM 값은 0~255 범위여야 합니다!");
//       }
//     } else {
//       Serial.println("잘못된 입력입니다!");
//     }
//   }
// }

// // PWM 값을 직접 설정하는 함수 (서보 모터처럼)
// void setPWM(int pwmValue) {
//   digitalWrite(STBY, HIGH);
  
//   // PWM 값에 따라 방향 결정
//   // 0~127: 역방향, 128: 정지, 129~255: 정방향
//   if (pwmValue < 128) {
//     // 역방향
//     digitalWrite(AIN1, LOW);
//     digitalWrite(AIN2, HIGH);
//     analogWrite(PWMA, 255 - pwmValue * 2); // 0~127을 255~1로 변환
//   } else if (pwmValue > 128) {
//     // 정방향
//     digitalWrite(AIN1, HIGH);
//     digitalWrite(AIN2, LOW);
//     analogWrite(PWMA, (pwmValue - 128) * 2); // 129~255를 2~254로 변환
//   } else {
//     // 정지 (128)
//     stop();
//   }
// }

// // 특정 각도로 이동하는 함수
// void moveToAngle(int targetAngle, int speed) {
//   // 각도 제한 확인
//   if (targetAngle < minAngle) {
//     targetAngle = minAngle;
//     Serial.print("최소 각도로 제한: ");
//     Serial.println(minAngle);
//   }
//   if (targetAngle > maxAngle) {
//     targetAngle = maxAngle;
//     Serial.print("최대 각도로 제한: ");
//     Serial.println(maxAngle);
//   }
  
//   int angleDiff = targetAngle - currentAngle;
  
//   if (angleDiff == 0) {
//     Serial.println("이미 목표 각도에 있습니다.");
//     return;
//   }
  
//   // 방향 결정
//   int direction = (angleDiff > 0) ? 1 : 0;
  
//   // 이동 시간 계산
//   unsigned long moveTime = abs(angleDiff) * msPerDegree;
  
//   Serial.print("각도 이동: ");
//   Serial.print(currentAngle);
//   Serial.print("도 -> ");
//   Serial.print(targetAngle);
//   Serial.print("도 (");
//   Serial.print(moveTime);
//   Serial.println("ms)");
  
//   // 모터 동작
//   move(1, speed, direction);
//   delay(moveTime);
//   stop();
  
//   // 현재 각도 업데이트
//   currentAngle = targetAngle;
  
//   Serial.print("이동 완료. 현재 각도: ");
//   Serial.println(currentAngle);
// }

// void move(int motor, int speed, int direction){
// //Move specific motor at speed and direction
// //motor: 0 for B 1 for A
// //speed: 0 is off, and 255 is full speed
// //direction: 0 clockwise, 1 counter-clockwise

//   digitalWrite(STBY, HIGH); //disable standby

//   boolean inPin1 = LOW;
//   boolean inPin2 = HIGH;

//   if(direction == 1){
//     inPin1 = HIGH;
//     inPin2 = LOW;
//   }

//   if(motor == 1){
//     digitalWrite(AIN1, inPin1);
//     digitalWrite(AIN2, inPin2);
//     analogWrite(PWMA, speed);
//   }
// }

// void stop(){
// //enable standby  
//   digitalWrite(STBY, LOW); 
// }

// // 문자열이 모두 숫자인지 확인하는 함수
// bool isNumeric(String str) {
//   for (int i = 0; i < str.length(); i++) {
//     if (!isDigit(str.charAt(i))) {
//       return false;
//     }
//   }
//   return true;
// }