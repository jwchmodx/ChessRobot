#!/bin/bash
# dataset_collector 실행 스크립트

# 스크립트 디렉토리 경로 (절대 경로)
SCRIPT_DIR="/home/chess/Desktop/ChessRobot/brain/aicv"

# 작업 디렉토리로 이동
cd "$SCRIPT_DIR" || {
    echo "Error: Cannot change to directory $SCRIPT_DIR"
    exit 1
}

# 가상환경 활성화
VENV_PATH="../venv/bin/activate"
if [ -f "$VENV_PATH" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH"
else
    echo "Warning: Virtual environment not found at $VENV_PATH"
    echo "Using system Python..."
fi

# dataset_collector 실행
echo "Starting dataset_collector..."
python3 dataset_collector.py "$@"

