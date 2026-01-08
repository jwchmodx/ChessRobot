// #include <Wire.h>
// #include <Adafruit_PWMServoDriver.h>

// // 서보 드라이버 채널 번호
// #define MOTOR_CHANNEL 2

// // 서보 MIN/MAX 펄스 값 (IKtest.ino의 0번 채널 값 참고)
// #define SERVO_MIN_PULSE 90   // 0도에 해당하는 펄스
// #define SERVO_MAX_PULSE 436  // 180도에 해당하는 펄스

// // 서보 드라이버 객체 생성
// Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// // 각도를 펄스 값으로 변환하는 함수
// int angleToPulse(float angle) {
//   // 각도를 0~180 범위로 제한
//   angle = constrain(angle, 0, 180);
//   // 0~180도를 MIN~MAX 펄스로 매핑
//   return map(angle, 0, 180, SERVO_MIN_PULSE, SERVO_MAX_PULSE);
// }

// void setup() {
//   Serial.begin(9600);
//   Serial.println("모터 각도 테스트 시작");
//   Serial.println("0번 채널 모터를 0도에서 180도까지 회전합니다.");
  
//   // 서보 드라이버 초기화
//   pwm.begin();
//   pwm.setOscillatorFrequency(27000000);
//   pwm.setPWMFreq(50); // 서보 모터는 50Hz
  
//   // 초기 위치: 0도
//   int pulse0 = angleToPulse(0);
//   pwm.setPWM(MOTOR_CHANNEL, 0, pulse0);
//   Serial.print("초기 위치: 0도 (펄스: ");
//   Serial.print(pulse0);
//   Serial.println(")");
  
//   delay(1000);
// }

// void loop() {
//   // 0도에서 180도까지 회전
//   Serial.println("\n=== 0도 → 180도 회전 ===");
//   for (int angle = 0; angle <= 180; angle += 5) {
//     int pulse = angleToPulse(angle);
//     pwm.setPWM(MOTOR_CHANNEL, 0, pulse);
    
//     Serial.print("각도: ");
//     Serial.print(angle);
//     Serial.print("도, 펄스: ");
//     Serial.println(pulse);
    
//     delay(100); // 각 단계마다 100ms 대기
//   }
  
//   delay(1000);
  
//   // 180도에서 0도까지 회전
//   Serial.println("\n=== 180도 → 0도 회전 ===");
//   for (int angle = 180; angle >= 0; angle -= 5) {
//     int pulse = angleToPulse(angle);
//     pwm.setPWM(MOTOR_CHANNEL, 0, pulse);
    
//     Serial.print("각도: ");
//     Serial.print(angle);
//     Serial.print("도, 펄스: ");
//     Serial.println(pulse);
    
//     delay(100); // 각 단계마다 100ms 대기
//   }
  
//   delay(2000); // 한 사이클 완료 후 2초 대기
// }


//motor A connected between A01 and A02
//motor B connected between B01 and B02

int STBY = 10; //standby

//Motor A
int PWMA = 3; //Speed control 
int AIN1 = 9; //Direction
int AIN2 = 8; //Direction


void setup(){
  pinMode(STBY, OUTPUT);

  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);

  
}

void loop(){
  move(1, 255, 1); //motor 1, full speed, left
  
  delay(1000); //go for 1 second
  stop(); //stop
  delay(250); //hold for 250ms until move again

  move(1, 128, 0); //motor 1, half speed, right

  delay(1000);
  stop();
  delay(250);
}


void move(int motor, int speed, int direction){
//Move specific motor at speed and direction
//motor: 0 for B 1 for A
//speed: 0 is off, and 255 is full speed
//direction: 0 clockwise, 1 counter-clockwise

  digitalWrite(STBY, HIGH); //disable standby

  boolean inPin1 = LOW;
  boolean inPin2 = HIGH;

  if(direction == 1){
    inPin1 = HIGH;
    inPin2 = LOW;
  }

  if(motor == 1){
    digitalWrite(AIN1, inPin1);
    digitalWrite(AIN2, inPin2);
    analogWrite(PWMA, speed);
  }
}

void stop(){
//enable standby  
  digitalWrite(STBY, LOW); 
}