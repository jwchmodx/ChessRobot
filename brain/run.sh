#!/bin/bash
# 체스 로봇 실행 스크립트 (brain 디렉토리용)

# brain 디렉토리로 이동
cd "$(dirname "$0")"

# 가상 환경 활성화
if [ -d "venv" ]; then
    echo "🔧 가상 환경 활성화 중..."
    source venv/bin/activate
else
    echo "❌ venv 디렉토리를 찾을 수 없습니다."
    echo "💡 venv를 생성하려면: python3 -m venv venv"
    exit 1
fi

# 게임 실행
echo "♔ 체스 로봇 게임 시작 ♔"
echo "=================================================="
python terminal_chess.py

# 가상 환경 비활성화
deactivate

