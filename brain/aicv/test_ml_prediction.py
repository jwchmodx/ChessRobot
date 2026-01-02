#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML 모델 예측 결과만 확인하는 간단한 테스트 스크립트
카메라에서 프레임을 읽어 ML 모델로 기물을 예측하고 결과를 콘솔에 출력합니다.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# 프로젝트 루트를 경로에 추가
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from aicv.ml_piece_detector import ChessPieceMLDetector
from cv.cv_web import USBCapture, ThreadSafeCapture


def print_grid(grid, title="ML 예측 결과"):
    """8x8 그리드를 콘솔에 보기 좋게 출력"""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print("   " + " ".join([str(i+1) for i in range(8)]))
    files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
    for r in range(8):
        row_str = f"{files[r]} "
        for c in range(8):
            val = grid[r, c]
            if val == 0:
                row_str += ". "
            elif val == 1:
                row_str += "W "
            elif val == 2:
                row_str += "B "
            else:
                row_str += "? "
        print(row_str)
    
    # 통계 출력
    empty_count = (grid == 0).sum()
    white_count = (grid == 1).sum()
    black_count = (grid == 2).sum()
    print(f"\n통계: 빈칸={empty_count}, 흰색={white_count}, 검은색={black_count}")
    print(f"{'='*50}\n")


def main():
    """메인 함수"""
    print("=" * 60)
    print("ML 기물 인식 테스트 스크립트")
    print("=" * 60)
    
    # 모델 경로 설정
    model_path = BASE_DIR / "aicv" / "models" / "chess_piece_model.pt"
    
    if not model_path.exists():
        print(f"[ERROR] 모델 파일을 찾을 수 없습니다: {model_path}")
        print("[INFO] 모델 파일 경로를 확인하세요.")
        return 1
    
    # ML 모델 로드
    print(f"[→] ML 모델 로드 중: {model_path}")
    try:
        detector = ChessPieceMLDetector(str(model_path))
        print(f"[✓] ML 모델 로드 완료 (device: {detector.device})")
    except Exception as e:
        print(f"[ERROR] ML 모델 로드 실패: {e}")
        return 1
    
    # 카메라 초기화
    print("[→] 카메라 초기화 중...")
    try:
        cap = USBCapture(rotate_90_cw=False, rotate_90_ccw=False, rotate_180=True)
        cap_wrapper = ThreadSafeCapture(cap)
        print(f"[✓] 카메라 초기화 완료 (/dev/video{cap.index})")
    except Exception as e:
        print(f"[ERROR] 카메라 초기화 실패: {e}")
        return 1
    
    # 카메라 테스트
    print("[→] 카메라 연결 테스트 중...")
    ret, test_frame = cap_wrapper.read()
    if not ret or test_frame is None:
        print("[ERROR] 카메라에서 프레임을 읽을 수 없습니다.")
        return 1
    h, w = test_frame.shape[:2]
    print(f"[✓] 카메라 테스트 성공: {w}x{h} 해상도")
    
    print("\n" + "=" * 60)
    print("예측 시작 (Ctrl+C로 종료)")
    print("=" * 60)
    print("[INFO] 매 2초마다 예측 결과를 출력합니다.\n")
    
    try:
        frame_count = 0
        while True:
            frame_count += 1
            
            # 프레임 읽기
            ret, frame = cap_wrapper.read()
            if not ret or frame is None:
                print("[WARNING] 프레임을 읽을 수 없습니다. 재시도 중...")
                time.sleep(0.5)
                continue
            
            # 와핑된 이미지 얻기
            try:
                from cv.cv_manager import warp_with_manual_corners
                warped_frame = warp_with_manual_corners(frame, size=400)
                
                if warped_frame is None:
                    print("[WARNING] 와핑 실패, 원본 프레임 사용")
                    warped_frame = frame
            except Exception as e:
                print(f"[WARNING] 와핑 실패: {e}, 원본 프레임 사용")
                warped_frame = frame
            
            # ML 예측 수행 (와핑된 이미지 사용)
            try:
                grid = detector.predict_frame(warped_frame)
                print_grid(grid, f"프레임 #{frame_count} - ML 예측 결과 (와핑된 이미지)")
            except Exception as e:
                print(f"[ERROR] 예측 실패: {e}")
                time.sleep(1)
                continue
            
            # 2초 대기
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n[INFO] 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n[ERROR] 예기치 않은 오류: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 정리
        print("[→] 리소스 정리 중...")
        try:
            cap_wrapper.release()
        except Exception:
            pass
        print("[✓] 종료 완료")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

