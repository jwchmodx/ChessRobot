// // ============================================================
// // 그리퍼 모터 테스트 - RobotArmIK.cpp 값 찾기용
// // RobotArmIK::gripOpen(), gripClose()에 사용할 값을 테스트
// // ============================================================

// // TB6612 모터 드라이버 핀 설정 (RobotArmIK.cpp와 동일)
// const int GRIP_STBY = 10; // standby
// const int GRIP_PWMA = 3;  // Speed control 
// const int GRIP_AIN1 = 9;  // Direction
// const int GRIP_AIN2 = 8;  // Direction

// void setup() {
//   Serial.begin(9600);
  
//   // 핀 모드 설정
//   pinMode(GRIP_STBY, OUTPUT);
//   pinMode(GRIP_PWMA, OUTPUT);
//   pinMode(GRIP_AIN1, OUTPUT);
//   pinMode(GRIP_AIN2, OUTPUT);

//   Serial.println("====================================");
//   Serial.println("  그리퍼 테스트 - 최적값 찾기");
//   Serial.println("====================================");
//   Serial.println("명령어:");
//   Serial.println("  auto0  - direction 0 자동 테스트");
//   Serial.println("  auto1  - direction 1 자동 테스트");
//   Serial.println("  auto   - 양방향 모두 자동 테스트");
//   Serial.println("");
//   Serial.println("  수동:  150,1 (speed,direction)");
//   Serial.println("  정지:  s 또는 stop");
//   Serial.println("====================================");
//   Serial.println("");
//   Serial.println("자동 테스트:");
//   Serial.println("  - speed 50~250을 10씩 증가");
//   Serial.println("  - 각 단계마다 1초 구동");
//   Serial.println("  - 그리퍼 동작 잘 관찰하세요!");
//   Serial.println("====================================");
//   Serial.println("");
// }

// void loop() {
//   if (Serial.available()) {
//     String input = Serial.readStringUntil('\n');
//     input.trim();
    
//     // ========== 정지 명령 ==========
//     if (input == "s" || input == "S" || input == "stop" || input == "STOP") {
//       gripMotorStop();
//       Serial.println(">>> 모터 정지");
//       Serial.println("");
//       return;
//     }
    
//     // ========== 자동 테스트 명령 ==========
//     if (input == "auto" || input == "AUTO") {
//       runAutoTest(0); // direction 0 테스트
//       delay(2000);
//       runAutoTest(1); // direction 1 테스트
//       return;
//     }
    
//     if (input == "auto0" || input == "AUTO0") {
//       runAutoTest(0);
//       return;
//     }
    
//     if (input == "auto1" || input == "AUTO1") {
//       runAutoTest(1);
//       return;
//     }
    
//     // ========== 수동 테스트 (speed,direction) ==========
//     int commaIndex = input.indexOf(',');
//     if (commaIndex > 0) {
//       String speedStr = input.substring(0, commaIndex);
//       String dirStr = input.substring(commaIndex + 1);
      
//       if (isNumeric(speedStr) && isNumeric(dirStr)) {
//         int speed = speedStr.toInt();
//         int direction = dirStr.toInt();
        
//         if (speed >= 0 && speed <= 255 && (direction == 0 || direction == 1)) {
//           testGripper(speed, direction);
//         } else {
//           Serial.println("[에러] speed(0-255), direction(0 또는 1)");
//         }
//       } else {
//         Serial.println("[에러] 숫자만 입력 가능");
//       }
//     } else {
//       Serial.println("====================================");
//       Serial.println("[에러] 올바른 명령어를 입력하세요");
//       Serial.println("  auto   - 자동 테스트");
//       Serial.println("  auto0  - direction 0만");
//       Serial.println("  auto1  - direction 1만");
//       Serial.println("  150,1  - 수동 테스트");
//       Serial.println("====================================");
//       Serial.println("");
//     }
//   }
// }

// // ============================================================
// // 자동 테스트 함수
// // ============================================================
// void runAutoTest(int direction) {
//   Serial.println("");
//   Serial.println("====================================");
//   Serial.print(">>> 자동 테스트 시작: direction ");
//   Serial.print(direction);
//   Serial.print(" (");
//   Serial.print(direction == 0 ? "CW" : "CCW");
//   Serial.println(")");
//   Serial.println("====================================");
//   Serial.println("");
//   Serial.println("잘 관찰하세요! (s 입력시 중단 가능)");
//   Serial.println("");
  
//   // speed 50부터 250까지 10씩 증가
//   for (int speed = 50; speed <= 250; speed += 10) {
//     // 중단 체크
//     if (Serial.available()) {
//       String cmd = Serial.readStringUntil('\n');
//       cmd.trim();
//       if (cmd == "s" || cmd == "S" || cmd == "stop") {
//         gripMotorStop();
//         Serial.println("");
//         Serial.println(">>> 테스트 중단됨");
//         Serial.println("");
//         return;
//       }
//     }
    
//     // 현재 값 출력
//     Serial.print(">>> speed=");
//     Serial.print(speed);
//     Serial.print(", dir=");
//     Serial.println(direction);
    
//     // 모터 구동
//     gripMotorMove(speed, direction);
//     delay(1000); // 1초 구동
//     gripMotorStop();
//     delay(500);  // 0.5초 대기
//   }
  
//   Serial.println("");
//   Serial.println("====================================");
//   Serial.println(">>> 자동 테스트 완료!");
//   Serial.println("====================================");
//   Serial.println("");
//   Serial.println("어떤 값에서 그리퍼가 잘 동작했나요?");
//   Serial.println("해당 값으로 수동 테스트해보세요!");
//   Serial.println("");
// }

// // ============================================================
// // 수동 테스트 함수
// // ============================================================
// void testGripper(int speed, int direction) {
//   Serial.println("====================================");
//   Serial.print(">>> 테스트: speed=");
//   Serial.print(speed);
//   Serial.print(", direction=");
//   Serial.print(direction);
//   Serial.print(" (");
//   Serial.print(direction == 0 ? "CW" : "CCW");
//   Serial.println(")");
  
//   // 실행
//   gripMotorMove(speed, direction);
//   delay(500); // 500ms 구동
//   gripMotorStop();
  
//   Serial.println(">>> 완료 (500ms 구동)");
//   Serial.println("");
//   Serial.println("그리퍼가 어떻게 움직였나요?");
//   Serial.println("  - 열렸으면: gripOpen()에 사용");
//   Serial.println("  - 닫혔으면: gripClose()에 사용");
//   Serial.println("====================================");
//   Serial.println("");
// }

// // ============================================================
// // RobotArmIK.cpp와 동일한 함수들
// // ============================================================
// void gripMotorMove(int speed, int direction) {
//   digitalWrite(GRIP_STBY, HIGH); // disable standby

//   bool inPin1 = LOW;
//   bool inPin2 = HIGH;

//   if (direction == 1) {
//     inPin1 = HIGH;
//     inPin2 = LOW;
//   }

//   digitalWrite(GRIP_AIN1, inPin1);
//   digitalWrite(GRIP_AIN2, inPin2);
//   analogWrite(GRIP_PWMA, speed);
// }

// void gripMotorStop() {
//   digitalWrite(GRIP_STBY, LOW); // enable standby
// }

// // 헬퍼 함수
// bool isNumeric(String str) {
//   if (str.length() == 0) return false;
//   for (int i = 0; i < str.length(); i++) {
//     if (!isDigit(str.charAt(i))) {
//       return false;
//     }
//   }
//   return true;
// }