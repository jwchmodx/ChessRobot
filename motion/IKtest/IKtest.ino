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

// 측정된 각 칸의 좌표 (x, y, z)
//a1 {-176 73 64}
//a2 {-178 120 60}
//a3 {-185 168 66}
//a4 {-185 218 70}
//a5 {-185 268 69}
//a6 {-190 318 73}
//a7 {-195 368 82}
//a8 {-200 419 90}
//b1 {-125 75 55}
//b2 {-128 124 60}
//b3 {-125 168 65}
//b4 {-129 220 70}
//b5 {-133 265 70}
//b6 {-135 315 80}
//b7 {-142 366 85}
//b8 {-143 422 85}
//c1 {-75 83 60}
//c2 {-74 128 59}
//c3 {-79 174 62}
//c4 {-78 225 69}
//c5 {-84 270 74}
//c6 {-86 320 73}
//c7 {-93 372 82}
//c8 {-98 430 85}
//d1 {-23 83 65}
//d2 {-20 130 56}
//d3 {-25 180 56}
//d4 {-28 225 67}
//d5 {-30 270 68}
//d6 {-29 315 74}
//d7 {-37 374 82}
//d8 {-32 429 92}
//e1 {30 75 63}
//e2 {30 127 60}
//e3 {23 177 60}
//e4 {23 223 64}
//e5 {18 273 75}
//e6 {15 320 78}
//e7 {13 376 85}
//e8 {5 428 90}
//f1 {82 70 56}
//f2 {82 125 60}
//f3 {78 175 66}
//f4 {73 225 70}
//f5 {70 275 73}
//f6 {68 325 75}
//f7 {60 377 85}
//f8 {63 435 83}
//g1 {130 75 59}
//g2 {130 125 61}
//g3 {125 170 65}
//g4 {125 222 75}
//g5 {123 270 75}
//g6 {121 322 78}
//g7 {118 375 85}
//g8 {118 430 83}
//h1 {175 75 65}
//h2 {173 123 65}
//h3 {173 173 73}
//h4 {173 225 73}
//h5 {173 273 73}
//h6 {172 325 77}
//h7 {170 378 85}
//h8 {172 435 92}







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
    { -176,  73, 64 }, // a1
    { -178, 120, 60 }, // a2
    { -185, 168, 66 }, // a3
    { -185, 218, 70 }, // a4
    { -185, 268, 69 }, // a5
    { -190, 318, 73 }, // a6
    { -195, 368, 82 }, // a7
    { -200, 419, 90 }  // a8
  },
  // b 파일
  {
    { -125,  75, 55 }, // b1
    { -128, 124, 60 }, // b2
    { -125, 168, 65 }, // b3
    { -129, 220, 70 }, // b4
    { -133, 265, 70 }, // b5
    { -135, 315, 80 }, // b6
    { -142, 366, 85 }, // b7
    { -143, 422, 85 }  // b8
  },
  // c 파일
  {
    { -75,  83, 60 }, // c1
    { -74, 128, 59 }, // c2
    { -79, 174, 62 }, // c3
    { -78, 225, 69 }, // c4
    { -84, 270, 74 }, // c5
    { -86, 320, 73 }, // c6
    { -93, 372, 82 }, // c7
    { -98, 430, 85 }  // c8
  },
  // d 파일
  {
    { -23,  83, 65 }, // d1
    { -20, 130, 56 }, // d2
    { -25, 180, 56 }, // d3
    { -28, 225, 67 }, // d4
    { -30, 270, 68 }, // d5
    { -29, 315, 74 }, // d6
    { -37, 374, 82 }, // d7
    { -32, 429, 92 }  // d8
  },
  // e 파일
  {
    { 30,  75, 63 }, // e1
    { 30, 127, 60 }, // e2
    { 23, 177, 60 }, // e3
    { 23, 223, 64 }, // e4
    { 18, 273, 75 }, // e5
    { 15, 320, 78 }, // e6
    { 13, 376, 85 }, // e7
    { 5,  428, 90 }  // e8
  },
  // f 파일
  {
    { 82,  70, 56 }, // f1
    { 82, 125, 60 }, // f2
    { 78, 175, 66 }, // f3
    { 73, 225, 70 }, // f4
    { 70, 275, 73 }, // f5
    { 68, 325, 75 }, // f6
    { 60, 377, 85 }, // f7
    { 63, 435, 83 }  // f8
  },
  // g 파일
  {
    { 130,  75, 59 }, // g1
    { 130, 125, 61 }, // g2
    { 125, 170, 65 }, // g3
    { 125, 222, 75 }, // g4
    { 123, 270, 75 }, // g5
    { 121, 322, 78 }, // g6
    { 118, 375, 85 }, // g7
    { 118, 430, 83 }  // g8
  },
  // h 파일
  {
    { 175,  75, 65 }, // h1
    { 173, 123, 65 }, // h2
    { 173, 173, 73 }, // h3
    { 173, 225, 73 }, // h4
    { 173, 273, 73 }, // h5
    { 172, 325, 77 }, // h6
    { 170, 378, 85 }, // h7
    { 172, 435, 92 }  // h8
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
      delay(100);
      robotArm.gripOpen();
      delay(100);
      robotArm.moveTo(fromC.x, fromC.y, fZ_pick);
      delay(400);
      robotArm.gripClose();
      delay(100);

      // 2) 말을 든 상태로 다시 들어올리기 (출발 칸 z + 50)
      robotArm.moveTo(fromC.x, fromC.y, fZ_open);
      delay(400);

      // 3) 목적 칸의 z + 50 높이로 이동
      float tZ_open = toC.z + 50.0;
      robotArm.moveTo(toC.x, toC.y, tZ_open);
      delay(400);

      // 4) 목적 칸 위에서 내려가기
      robotArm.moveTo(toC.x, toC.y, tZ_place);
      delay(100);

      // 5) 말 내려놓기
      robotArm.gripOpen();
      delay(100);

      // 6) 다시 z + 50 높이로 올라가기
      robotArm.moveTo(toC.x, toC.y, tZ_open);
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
        robotArm.moveTo(c.x, c.y, zOpen);
        delay(400);
        robotArm.gripOpen();
        delay(400);
        robotArm.moveTo(c.x, c.y, zPick);
        delay(400);
        robotArm.gripClose();
        delay(400);
        robotArm.moveTo(c.x, c.y, zPick+120);

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
