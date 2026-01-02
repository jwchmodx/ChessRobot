// #include <Wire.h>
// #include <Adafruit_PWMServoDriver.h>

// #define GRIP_CHANNEL 3

// // 서보 드라이버 객체 생성
// Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// void setup() {
//   Serial.begin(9600);
  
//   // 서보 드라이버 초기화
//   pwm.begin();
//   pwm.setOscillatorFrequency(27000000);
//   pwm.setPWMFreq(50); // 서보 모터는 50Hz
  
//   Serial.println("그리퍼 PWM 테스트 시작");
//   Serial.println("숫자를 입력하면 그 PWM값으로 그리퍼가 움직입니다 (예: 210, 230 등)");
//   Serial.println("범위: 210~230 (또는 servoMaxs/servoMins 값)");
// }

// void loop() {
//   if (Serial.available()) {
//     String input = Serial.readStringUntil('\n');
//     input.trim();
    
//     // 입력값이 숫자인지 확인
//     if (input.length() > 0 && isNumeric(input)) {
//       int pwmValue = input.toInt();
      
//       Serial.print("그리퍼 PWM값 설정: ");
//       Serial.println(pwmValue);
      
//       // PWM값 설정
//       pwm.setPWM(GRIP_CHANNEL, 0, pwmValue);
      
//       delay(500);
//     } else {
//       Serial.println("숫자를 입력해주세요!");
//     }
//   }
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