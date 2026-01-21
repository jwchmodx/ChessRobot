#include <TM1637Display.h>

// 버튼 핀
#define BTN1 A2
#define BTN2 A3

// Player1용 TM1637 (정상 방향)
#define CLK1 A1
#define DIO1 A0
TM1637Display display1(CLK1, DIO1);

// Player2용 TM1637 (180도 회전 설치)
#define CLK2 A5
#define DIO2 A4
TM1637Display display2(CLK2, DIO2);

int time_p1 = 600; // 10분
int time_p2 = 600;
bool turn_p1 = false; // P2(흰색)부터 감소
bool timer_running = false; // 대기 상태로 시작 (start 신호 대기)
unsigned long prevMillis = 0;

// [추가됨] 180도 뒤집힌 숫자 패턴 배열 (0~9)
// 글자 모양을 상하좌우 반전시킨 비트맵입니다.
const uint8_t flipped_digits[] = {
  0b00111111, // 0
  0b00110000, // 1
  0b01011011, // 2
  0b01111001, // 3
  0b01110100, // 4
  0b01101101, // 5
  0b01101111, // 6
  0b00111000, // 7
  0b01111111, // 8
  0b01111101  // 9
};

void setup()
{
  Serial.begin(9600); 

  pinMode(BTN1, INPUT_PULLUP);
  pinMode(BTN2, INPUT_PULLUP);

  display1.setBrightness(2);
  display2.setBrightness(7);
  
  turn_p1 = false;
  timer_running = false; // start 신호 대기
  prevMillis = millis();
}

void loop()
{
  unsigned long now = millis();

  // 라즈베리파이로부터 명령어 수신
  if (Serial.available() > 0)
  {
    String command = Serial.readStringUntil('\n');
    command.trim(); // 공백 제거
    
    if (command == "start")
    {
      // 타이머 초기화 및 시작
      time_p1 = 600; // 10:00
      time_p2 = 600; // 10:00
      turn_p1 = false; // P2부터 감소
      timer_running = true;
      prevMillis = millis();
      
      Serial.println("Timer started: 10:00, 10:00");
    }
    else if (command == "end")
    {
      // 타이머 정지
      timer_running = false;
      Serial.println("Timer stopped");
    }
    else if (command == "black")
    {
      // 검은색(black) 플레이어가 수를 둠 -> 턴 전환
      turn_p1 = !turn_p1;
      Serial.print("Turn switched to: ");
      Serial.println(turn_p1 ? "P1" : "P2");
    }
  }

  // 타이머 로직 (1초마다 감소)
  if (timer_running && now - prevMillis >= 1000)
  {
    prevMillis = now;
    if (turn_p1 && time_p1 > 0)
      time_p1--;
    if (!turn_p1 && time_p2 > 0)
      time_p2--;

    // 시리얼 전송
    Serial.print("P1:");
    Serial.print(time_p1);
    Serial.print(",P2:");
    Serial.println(time_p2);
  }

  // 버튼 로직
  if (digitalRead(BTN1) == LOW)
  {
    turn_p1 = false;
    delay(200); 
  }
  if (digitalRead(BTN2) == LOW)
  {
    turn_p1 = true;
    delay(200);
  }

  // --- [Player 1] 화면 표시 (정상 출력) ---
  int p1_display = (time_p1 / 60) * 100 + (time_p1 % 60);
  display1.showNumberDecEx(p1_display, 0b01000000, true);


  // --- [Player 2] 화면 표시 (180도 회전 출력) ---
  // 1. 시, 분, 초 자릿수 분리
  int m1 = (time_p2 / 60) / 10; // 분 10의 자리
  int m2 = (time_p2 / 60) % 10; // 분 1의 자리
  int s1 = (time_p2 % 60) / 10; // 초 10의 자리
  int s2 = (time_p2 % 60) % 10; // 초 1의 자리

  // 2. 데이터 생성 (순서를 거꾸로 배치: s2, s1, m2, m1)
  uint8_t data[] = { 
    flipped_digits[s2], 
    flipped_digits[s1], 
    flipped_digits[m2], 
    flipped_digits[m1] 
  };

  // 3. 콜론(:) 추가 (물리적으로 가운데 위치한 s1 자리에 점을 찍음)
// 기존 코드
// data[1] = data[1] | 0b01000000; 

// 수정 코드 (최상위 비트가 보통 점/콜론을 담당함)
  data[1] = data[1] | 0b10000000;

  // 4. 화면에 전송
  display2.setSegments(data);
}