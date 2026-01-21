#include "RobotArmIK.h"

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include "RobotArmIK.h" // 수정된 라이브러리 호출

// --- 설정값 ---
// 서보 드라이버 채널 번호 (0부터 15까지)
#define SHOULDER_CHANNEL 0
#define UPPER_ARM_CHANNEL 1
#define LOWER_ARM_CHANNEL 2
#define GRIP_CHANNEL 3


#define DEAD_ZONE 250.0              // 잡은 말을 놓는 구역의 좌표



// 링크 길이 (mm)
const float L1 = 300.0;
const float L2 = 350.0;

// 서보별 MIN/MAX 값
int servoMins[NUM_SERVOS] = {85, 90, 75, 210}; // 각 서보 최소 펄스
int servoMaxs[NUM_SERVOS] = {455, 436, 445, 230}; // 각 서보 최대 펄스


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
  // h 파일
  {
    { -183,  63, 67 }, // h8
    { -183, 110, 60 }, // h7
    { -185, 165, 73 }, // h6
    { -187, 215, 75 }, // h5
    { -193, 260, 86 }, // h4
    { -205, 312, 95 }, // h3
    { -203, 363, 110 }, // h2
    { -213, 415, 110 }  // h1
  },
  // g 파일
  {
    { -136,  70, 48 }, // g8
    { -135, 120, 56 }, // g7
    { -130, 168, 65 }, // g6
    { -135, 219, 70 }, // g5
    { -138, 260, 80 }, // g4
    { -145, 315, 85 }, // g3
    { -150, 368, 94 }, // g2
    { -158, 422, 96 }  // g1
  },
  // f 파일
  {
    { -81,  70, 50 }, // f8
    { -85, 126, 52 }, // f7
    { -83, 177, 70 }, // f6
    { -83, 218, 69 }, // f5
    { -92, 275, 83 }, // f4
    { -96, 320, 84 }, // f3
    { -106, 373, 90 }, // f2
    { -109, 430, 100 }  // f1
  },
  // e 파일
  {
    { -26,  72, 62 }, // e8
    { -32, 130, 56 }, // e7
    { -30, 181, 63 }, // e6
    { -34, 228, 75 }, // e5
    { -32, 274, 72 }, // e4
    { -37, 321, 780 }, // e3
    { -42, 374, 82 }, // e2
    { -38, 430, 100 }  // e1
  },
  // d 파일
  {
    { 23,  77, 60 }, // d8
    { 22, 130, 57 }, // d7
    { 20, 172, 57 }, // d6
    { 15, 226, 66 }, // d5
    { 18, 273, 75 }, // d4
    { 9, 324, 78 }, // d3
    { 5, 376, 88 }, // d2
    { -2,  434, 96 }  // d1
  },
  // c 파일
  {
    { 75,  75, 56 }, // c8
    { 79, 128, 53 }, // c7
    { 75, 178, 66 }, // c6
    { 73, 232, 70 }, // c5
    { 68, 280, 76 }, // c4
    { 65, 328, 75 }, // c3
    { 60, 382, 90 }, // c2
    { 58, 435, 95 }  // c1
  },
  // b 파일
  {
    { 130,  79, 50 }, // b8
    { 130, 128, 58 }, // b7
    { 121, 172, 65 }, // b6
    { 125, 224, 75 }, // b5
    { 120, 274, 75 }, // b4
    { 115, 327, 90 }, // b3
    { 115, 381, 89 }, // b2
    { 114, 435, 92 }  // b1
  },
  // a 파일
  {
    { 180,  75, 65 }, // a8
    { 175, 126, 65 }, // a7
    { 176, 176, 73 }, // a6
    { 167, 227, 75 }, // a5
    { 171, 273, 76 }, // a4
    { 170, 328, 85 }, // a3
    { 167, 386, 105 }, // a2
    { 167, 440, 105 }  // a1
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



// 현재 로봇 팔의 마지막 위치를 기억하기 위한 변수
float curX = 365.0;
float curY = 0.0;
float curZ = 330.0;

// 항상 이 함수를 통해 moveTo를 호출해서 현재 위치를 갱신
void moveArmTo(float x, float y, float z) {
  robotArm.moveTo(x, y, z);
  curX = x;
  curY = y;
  curZ = z;
}



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

  moveArmTo(365,0,330); // 시작 준비 자세

 
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

      moveArmTo(x, y, z);
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
      Serial.println("ZERO 명령 수신: 제로 포지션으로 이동 (현재 위치에서 z만 살짝 올린 뒤 이동)");

      // 1) 현재 좌표에서 z만 올리기 (x, y는 그대로 유지)
      float liftZ = curZ + 80.0;   // 얼마나 올릴지 (필요하면 조정)
      moveArmTo(curX, curY, liftZ);
      delay(500);

      // 2) 제로 포지션으로 이동
      moveArmTo(365, 0, 330); // setup에서 사용한 준비 자세와 동일
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
      float fZ_open  = fromC.z + 100.0;  // 그리퍼를 여는 높이
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
      moveArmTo(fromC.x, fromC.y, fZ_open);
      delay(100);
      robotArm.gripOpen();
      delay(100);
      moveArmTo(fromC.x, fromC.y, fZ_pick + 4);
      delay(400);
      robotArm.gripClose();
      delay(100);

      // 2) 말을 든 상태로 다시 들어올리기 (출발 칸 z + 50)
      moveArmTo(fromC.x, fromC.y, fZ_open);
      delay(400);

      // 3) 목적 칸의 z + 100 높이로 이동
      float tZ_open = toC.z + 100.0;
      moveArmTo(toC.x, toC.y, tZ_open);
      delay(400);

      // 4) 목적 칸 위에서 내려가기
      moveArmTo(toC.x, toC.y, tZ_place);
      delay(100);

      // 5) 말 내려놓기
      robotArm.gripOpen();
      delay(100);

      // 6) 다시 z + 50 높이로 올라가기
      moveArmTo(toC.x, toC.y, tZ_open);
      delay(100);

      Serial.println("movecomplete");
    }
    // 단일 좌표 명령 처리 ("e4" 또는 "e4cap")
    else if (square.length() == 2) {
      float x, y;
      int colIdx, rowIdx;

      chessToCoordinates(square, x, y, colIdx, rowIdx);
      Coord c = complete_coordinates[colIdx][rowIdx];

      float zPick = c.z;         // 말을 잡는 높이
      float zOpen = c.z + 120.0;  // 그리퍼를 여는 높이

      Serial.print("입력: "); Serial.println(pos);
      Serial.print("계산된 좌표 -> x: "); Serial.print(c.x);
      Serial.print(", y: "); Serial.print(c.y);
      Serial.print(", z: "); Serial.println(c.z);

      if (isCapture) {
        // 1) 잡을 말 위치로 이동해서 집기
        moveArmTo(c.x, c.y, zOpen);
        delay(400);
        robotArm.gripOpen();
        delay(400);
        moveArmTo(c.x, c.y, zPick + 4);
        delay(400);
        robotArm.gripClose();
        delay(400);
        moveArmTo(c.x, c.y, zPick+120);

        // 2) DEAD_ZONE으로 이동해서 버리기
        moveArmTo(380, DEAD_ZONE, 150);
        delay(400);
        robotArm.gripOpen(); 
        moveArmTo(-355, 0, 300);


        Serial.println("movecomplete");

      } else {
        // 단일 위치 테스트: 해당 위치로 이동 후 집었다가 놓기
        moveArmTo(c.x, c.y, zPick + 4);
        delay(1000);
        robotArm.gripClose(); delay(1000);
        robotArm.gripOpen();  delay(1000);
        Serial.println("movecomplete");
      }
    }
  delay(500);  // 입력 템포 조절
  }
}
