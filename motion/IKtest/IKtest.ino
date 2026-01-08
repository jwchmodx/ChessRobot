#include "RobotArmIK.h"

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include "RobotArmIK.h" // 수정된 라이브러리 호출

// --- 설정값 ---
// 서보 드라이버 채널 번호 (0부터 15까지)
#define SHOULDER_CHANNEL 0
#define UPPER_ARM_CHANNEL 1
#define LOWER_ARM_CHANNEL 2



#define DEAD_ZONE 250.0              // 잡은 말을 놓는 구역의 좌표



// 링크 길이 (mm)
const float L1 = 300.0;
const float L2 = 350.0;

// 서보별 MIN/MAX 값
int servoMins[NUM_SERVOS] = {85, 90, 75, 210}; // 각 서보 최소 펄스
int servoMaxs[NUM_SERVOS] = {455, 436, 445, 230}; // 각 서보 최대 펄스

// 측정된 각 칸의 좌표 (x, y, z)
//a1 {-167 70 60}
//a2 {-167 112 60}
//a3 {-172 160 70}
//a4 {-180 210 75}
//a5 {-180 255 75}
//a6 {-185 310 80}
//a7 {-185 370 90}
//a8 {-198 415 90}
//b1 {-123 75 60}
//b2 {-125 116 60}
//b3 {-125 165 65}
//b4 {-127 215 70}
//b5 {-130 265 70}
//b6 {-134 315 75}
//b7 {-136 365 85}
//b8 {-139 420 90}
//c1 {-75 83 60}
//c2 {-75 135 60}
//c3 {-75 175 65}
//c4 {-75 225 70}
//c5 {-83 270 73}
//c6 {-83 320 73}
//c7 {-86 372 80}
//c8 {-98 430 85}
//d1 {-23 83 65}
//d2 {-20 130 65}
//d3 {-20 180 65}
//d4 {-25 225 65}
//d5 {-25 270 65}
//d6 {-25 315 70}
//d7 {-32 373 78}
//d8 {-32 428 85}
//e1 {35 80 65}
//e2 {35 130 65}
//e3 {32 180 65}
//e4 {26 223 65}
//e5 {23 273 70}
//e6 {18 317 70}
//e7 {18 373 80}
//e8 {13 428 85}
//f1 {82 75 65}
//f2 {82 125 65}
//f3 {78 175 66}
//f4 {78 225 66}
//f5 {75 275 70}
//f6 {73 325 75}
//f7 {70 377 85}
//f8 {68 435 88}
//g1 {130 75 65}
//g2 {130 125 65}
//g3 {125 172 70}
//g4 {125 222 75}
//g5 {123 270 78}
//g6 {121 322 78}
//g7 {118 375 85}
//g8 {118 430 88}
//h1 {178 75 60}
//h2 {173 123 65}
//h3 {173 173 70}
//h4 {173 225 73}
//h5 {173 273 73}
//h6 {172 325 77}
//h7 {172 378 85}
//h8 {172 433 88}







// 사용되지 않는 변수 (참고용 주석)

// 실제로 사용할 좌표 테이블
struct Coord {
  float x;
  float y;
  float z;
};

// complete_coordinates[fileIndex][rankIndex]
// fileIndex: a=0, b=1, ... h=7
// rankIndex: 1=0, 2=1, ... 8=7
Coord complete_coordinates[8][8] = {
  // a 파일
  {
    { -167,  70, 60 }, // a1
    { -167, 112, 60 }, // a2
    { -172, 160, 70 }, // a3
    { -180, 210, 75 }, // a4
    { -180, 255, 75 }, // a5
    { -185, 310, 80 }, // a6
    { -185, 370, 90 }, // a7
    { -198, 415, 90 }  // a8
  },
  // b 파일
  {
    { -123,  75, 60 }, // b1
    { -125, 116, 60 }, // b2
    { -125, 165, 65 }, // b3
    { -127, 215, 70 }, // b4
    { -130, 265, 70 }, // b5
    { -134, 315, 75 }, // b6
    { -136, 365, 85 }, // b7
    { -139, 420, 90 }  // b8
  },
  // c 파일
  {
    { -75,  83, 60 }, // c1
    { -75, 135, 60 }, // c2
    { -75, 175, 65 }, // c3
    { -75, 225, 70 }, // c4
    { -83, 270, 73 }, // c5
    { -83, 320, 73 }, // c6
    { -86, 372, 80 }, // c7
    { -98, 430, 85 }  // c8
  },
  // d 파일
  {
    { -23,  83, 65 }, // d1
    { -20, 130, 65 }, // d2
    { -20, 180, 65 }, // d3
    { -25, 225, 65 }, // d4
    { -25, 270, 65 }, // d5
    { -25, 315, 70 }, // d6
    { -32, 373, 78 }, // d7
    { -32, 428, 85 }  // d8
  },
  // e 파일
  {
    { 35,  80, 65 }, // e1
    { 35, 130, 65 }, // e2
    { 32, 180, 65 }, // e3
    { 26, 223, 65 }, // e4
    { 23, 273, 70 }, // e5
    { 18, 317, 70 }, // e6
    { 18, 373, 80 }, // e7
    { 13, 428, 85 }  // e8
  },
  // f 파일
  {
    { 82,  75, 65 }, // f1
    { 82, 125, 65 }, // f2
    { 78, 175, 66 }, // f3
    { 78, 225, 66 }, // f4
    { 75, 275, 70 }, // f5
    { 73, 325, 75 }, // f6
    { 70, 377, 85 }, // f7
    { 68, 435, 88 }  // f8
  },
  // g 파일
  {
    { 130,  75, 65 }, // g1
    { 130, 125, 65 }, // g2
    { 125, 172, 70 }, // g3
    { 125, 222, 75 }, // g4
    { 123, 270, 78 }, // g5
    { 121, 322, 78 }, // g6
    { 118, 375, 85 }, // g7
    { 118, 430, 88 }  // g8
  },
  // h 파일
  {
    { 178,  75, 60 }, // h1
    { 173, 123, 65 }, // h2
    { 173, 173, 70 }, // h3
    { 173, 225, 73 }, // h4
    { 173, 273, 73 }, // h5
    { 172, 325, 77 }, // h6
    { 172, 378, 85 }, // h7
    { 172, 433, 88 }  // h8
  }
};



// 체스 표기법 배열
// 주의: 변수명과 실제 의미가 다름!
// rows는 실제로 files (a-h, 열)
// columns는 실제로 ranks (1-8, 행)
char files[8] = {'h', 'g', 'f', 'e', 'd', 'c', 'b', 'a'};  // 파일 (열)
char ranks[8] = {'8', '7', '6', '5', '4', '3', '2', '1'};  // 랭크 (행)

// 좌표 매핑 배열
float map_x[8];
float map_y[8];


// --- 객체 생성 ---
// 1. 서보 드라이버 객체 생성
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

// 2. RobotArmIK 객체 생성 (핀 번호 대신 채널 번호와 드라이버 객체의 주소(&pwm)를 전달)
RobotArmIK robotArm(&pwm, SHOULDER_CHANNEL, UPPER_ARM_CHANNEL, LOWER_ARM_CHANNEL, GRIP_CHANNEL, L1, L2, servoMins, servoMaxs);



bool parseXYZ(String input, float &x, float &y, float &z) {
  int firstSpace = input.indexOf(' ');
  int secondSpace = input.indexOf(' ', firstSpace + 1);

  if (firstSpace == -1 || secondSpace == -1) return false;

  x = input.substring(0, firstSpace).toFloat();
  y = input.substring(firstSpace + 1, secondSpace).toFloat();
  z = input.substring(secondSpace + 1).toFloat();

  return true;
}

// 체스 표기법을 좌표 인덱스로 변환하고, 측정된 좌표 테이블에서 x, y를 꺼내는 함수
// (z 값은 complete_coordinates[colIndexOut][rowIndexOut].z 를 사용)
void chessToCoordinates(String chessPos, float &x, float &y, int &colIndexOut, int &rowIndexOut)
{
  colIndexOut = -1;
  rowIndexOut = -1;

  if (chessPos.length() != 2)
  {
    x = 0;
    y = 0;
    return;
  }

  char file = chessPos.charAt(0); // a, b, c, d, e, f, g, h (열, 좌우)
  char rank = chessPos.charAt(1); // 1, 2, 3, 4, 5, 6, 7, 8 (행, 앞뒤)

  // 파일 인덱스 찾기 (a=0, b=1, ..., h=7)
  int fileIndex = -1;
  for (int i = 0; i < 8; i++)
  {
    if (files[i] == file)
    {
      fileIndex = i;
      break;
    }
  }

  // 랭크 인덱스 찾기 (1=0, 2=1, ..., 8=7)
  int rankIndex = -1;
  for (int i = 0; i < 8; i++)
  {
    if (ranks[i] == rank)
    {
      rankIndex = i;
      break;
    }
  }

  if (fileIndex >= 0 && rankIndex >= 0)
  {
    int colIndex = fileIndex;
    int rowIndex = rankIndex;

    Coord c = complete_coordinates[colIndex][rowIndex];
    x = c.x;
    y = c.y;
    colIndexOut = colIndex;
    rowIndexOut = rowIndex;
  }
  else
  {
    x = 0;
    y = 0;
  }
}




void setup()
{
  Serial.begin(9600);

  // 서보 드라이버 초기화
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setPWMFreq(50); // 서보 모터는 50Hz

  // robotArm.begin(); // 라이브러리의 begin()은 현재 비어있으므로 생략 가능
    Serial.println("체스 로봇 좌표 시스템 초기화 완료");

  robotArm.moveTo(-355,0,300); // 시작 준비 자세

 
  delay(2000);
}


void loop() {

  if (Serial.available()) {
    // 라즈베리파이(brain)에서 들어오는 명령 처리
    // - 일반 이동: "e2e4" (from→to)
    // - 캡처: "e4cap" (상대 말 제거), 이후 "e2e4" 등
    // - 단일 좌표 테스트: "e2"
    // - 제로 포지션: "zero"

    String pos = Serial.readStringUntil('\n');
    pos.trim();

    float x, y, z;
    if (parseXYZ(pos, x, y, z)) {
      Serial.println("숫자 좌표 입력 감지");
      Serial.print("x: "); Serial.print(x);
      Serial.print(", y: "); Serial.print(y);
      Serial.print(", z: "); Serial.println(z);

      robotArm.moveTo(x, y, z);
      Serial.println("movecomplete");
      delay(500);
      return;  // 중요: 문자열 명령 처리로 안 넘어가게
    }


    bool isCapture    = false;
    bool isZero       = false;
    bool isFullMove   = false;
    bool isGripOpen   = false;
    bool isGripClose  = false;
    String square      = ""; // 단일 좌표 명령용 ("e4", "e4cap"에서 "e4")
    String fromSquare  = ""; // 전체 이동 from ("e2e4" → "e2")
    String toSquare    = ""; // 전체 이동 to   ("e2e4" → "e4")

    // 제로 포지션 명령
    if (pos.equalsIgnoreCase("zero")) {
      isZero = true;
    }
    // 그리퍼 테스트 명령
    else if (pos.equalsIgnoreCase("gripopen")) {
      isGripOpen = true;
    }
    else if (pos.equalsIgnoreCase("gripclose")) {
      isGripClose = true;
    }
    else if (pos.equalsIgnoreCase("open")) {
      isGripOpen = true;
    }
    else if (pos.equalsIgnoreCase("close")) {
      isGripClose = true;
    }
    // "e4cap" 같은 형식 감지 (캡처용 단일 좌표 명령)
    else if (pos.endsWith("cap") && pos.length() >= 5) {
      square = pos.substring(0, 2); // 앞 2글자만 체스 좌표
      isCapture = true;
    }
    // 전체 이동 명령 (예: "e2e4")
    else if (pos.length() == 4) {
      fromSquare = pos.substring(0, 2);
      toSquare   = pos.substring(2, 4);
      isFullMove = true;
    }
    // 일반 체스 좌표 (예: "e2")
    else if (pos.length() == 2) {
      square = pos;
    }

    if (isZero) {
      // 제로 포지션으로 복귀
      Serial.println("ZERO 명령 수신: 제로 포지션으로 이동");
      robotArm.moveTo(365, 0, 330); // setup에서 사용한 준비 자세와 동일
      delay(1000);
    }
    else if (isGripOpen) {
      Serial.println("GRIPOPEN 명령 수신: 그리퍼 열기");
      robotArm.gripOpen();
      delay(300);
    }
    else if (isGripClose) {
      Serial.println("GRIPCLOSE 명령 수신: 그리퍼 닫기");
      robotArm.gripClose();
      delay(300);
    }
    // 전체 이동 명령 처리 ("e2e4"처럼 from → to)
    else if (isFullMove && fromSquare.length() == 2 && toSquare.length() == 2) {
      float fx, fy, tx, ty;
      int fCol, fRow, tCol, tRow;
      chessToCoordinates(fromSquare, fx, fy, fCol, fRow);
      chessToCoordinates(toSquare,   tx, ty, tCol, tRow);

      // 측정된 좌표에서 z 사용
      Coord fromC = complete_coordinates[fCol][fRow];
      Coord toC   = complete_coordinates[tCol][tRow];

      float fZ_pick  = fromC.z;         // 말을 잡는 높이
      float fZ_open  = fromC.z + 50.0;  // 그리퍼를 여는 높이
      float tZ_place = toC.z;           // 말을 놓는 높이

      Serial.print("입력(전체 이동): "); Serial.println(pos);
      Serial.print("FROM -> x: "); Serial.print(fromC.x);
      Serial.print(", y: "); Serial.print(fromC.y);
      Serial.print(", z: "); Serial.println(fromC.z);
      Serial.print("TO   -> x: "); Serial.print(toC.x);
      Serial.print(", y: "); Serial.print(toC.y);
      Serial.print(", z: "); Serial.println(toC.z);

      // 1) 출발 칸으로 이동해서 말을 집기
      //    (먼저 위쪽에서 접근 → 내려가서 집기)
      robotArm.moveTo(fromC.x, fromC.y, fZ_open);
      delay(400);
      robotArm.gripOpen();
      delay(400);
      robotArm.moveTo(fromC.x, fromC.y, fZ_pick);
      delay(800);
      robotArm.gripClose();
      delay(400);

      // 2) 말을 든 상태로 다시 들어올리기 (출발 칸 z + 50)
      robotArm.moveTo(fromC.x, fromC.y, fZ_open);
      delay(400);

      // 3) 목적 칸의 z + 50 높이로 이동
      float tZ_open = toC.z + 50.0;
      robotArm.moveTo(toC.x, toC.y, tZ_open);
      delay(400);

      // 4) 목적 칸 위에서 천천히 내려가기
      //    (여러 단계로 z를 줄여서 보다 느리게 접근)
      float midZ1 = tZ_open - 20.0;
      float midZ2 = tZ_open - 20.0;
      if (midZ1 > tZ_place) {
        robotArm.moveTo(toC.x, toC.y, midZ1);
        delay(300);
      }
      if (midZ2 > tZ_place) {
        robotArm.moveTo(toC.x, toC.y, midZ2);
        delay(300);
      }
      robotArm.moveTo(toC.x, toC.y, tZ_place);
      delay(400);

      // 5) 말 내려놓기
      robotArm.gripOpen();
      delay(400);

      // 6) 다시 z + 50 높이로 올라가기
      robotArm.moveTo(toC.x, toC.y, tZ_open);
      delay(400);

      // 7) 제로 포지션으로 복귀
      robotArm.moveTo(-355, 0, 300);
      delay(500);
      Serial.println("movecomplete");
    }
    // 단일 좌표 명령 처리 ("e4" 또는 "e4cap")
    else if (square.length() == 2) {
      float x, y;
      int colIdx, rowIdx;

      chessToCoordinates(square, x, y, colIdx, rowIdx);
      Coord c = complete_coordinates[colIdx][rowIdx];

      float zPick = c.z;         // 말을 잡는 높이
      float zOpen = c.z + 100.0;  // 그리퍼를 여는 높이

      Serial.print("입력: "); Serial.println(pos);
      Serial.print("계산된 좌표 -> x: "); Serial.print(c.x);
      Serial.print(", y: "); Serial.print(c.y);
      Serial.print(", z: "); Serial.println(c.z);

      if (isCapture) {
        // 1) 잡을 말 위치로 이동해서 집기
        robotArm.moveTo(c.x, c.y, zOpen);
        delay(400);
        robotArm.gripOpen();
        delay(400);
        robotArm.moveTo(c.x, c.y, zPick);
        delay(400);
        robotArm.gripClose();
        delay(400);
        robotArm.moveTo(c.x, c.y, zPick+100);

        // 2) DEAD_ZONE으로 이동해서 버리기
        robotArm.moveTo(380, DEAD_ZONE, 150);
        delay(400);
        robotArm.gripOpen(); 
        robotArm.moveTo(-355, 0, 300);


        Serial.println("movecomplete");

      } else {
        // 단일 위치 테스트: 해당 위치로 이동 후 집었다가 놓기
        robotArm.moveTo(c.x, c.y, zPick);
        delay(1000);
        robotArm.gripClose(); delay(1000);
        robotArm.gripOpen();  delay(1000);
        Serial.println("movecomplete");
      }
    }
  delay(500);  // 입력 템포 조절
  }
}
