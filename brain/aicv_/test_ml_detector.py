#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML 기물 인식 테스트 스크립트
"""

import sys
import os
from pathlib import Path

# brain 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "brain"))

import cv2
import numpy as np
from cv.ml_piece_detector import ChessPieceMLDetector, detect_pieces_ml


def main():
    """테스트 메인 함수"""
    # 모델 경로 설정 (실제 모델 파일 경로로 변경 필요)
    model_path = input("모델 파일 경로를 입력하세요 (.pt 파일): ").strip()
    
    if not os.path.exists(model_path):
        print(f"[ERROR] 모델 파일을 찾을 수 없습니다: {model_path}")
        return
    
    # 이미지 경로 또는 카메라 사용
    use_camera = input("카메라를 사용하시겠습니까? (y/n): ").strip().lower() == 'y'
    
    if use_camera:
        # 카메라 캡처
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[ERROR] 카메라를 열 수 없습니다.")
            return
        
        print("[INFO] 카메라에서 프레임을 읽는 중... (q를 눌러 종료)")
        
        detector = ChessPieceMLDetector(model_path)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # 예측
            grid = detector.predict_frame(frame)
            
            # 결과 시각화
            vis = frame.copy()
            H, W = vis.shape[:2]
            cell_h, cell_w = H // 8, W // 8
            
            for r in range(8):
                for c in range(8):
                    pred = grid[r, c]
                    x0, y0 = c * cell_w, r * cell_h
                    x1, y1 = (c + 1) * cell_w, (r + 1) * cell_h
                    
                    if pred == 1:  # white
                        cv2.rectangle(vis, (x0, y0), (x1, y1), (255, 255, 255), 2)
                        cv2.putText(vis, "W", (x0 + 5, y0 + 20), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    elif pred == 2:  # black
                        cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 0, 0), 2)
                        cv2.putText(vis, "B", (x0 + 5, y0 + 20), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            
            cv2.imshow("ML Piece Detection", vis)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cap.release()
        cv2.destroyAllWindows()
    else:
        # 이미지 파일 사용
        img_path = input("이미지 파일 경로를 입력하세요: ").strip()
        
        if not os.path.exists(img_path):
            print(f"[ERROR] 이미지 파일을 찾을 수 없습니다: {img_path}")
            return
        
        img = cv2.imread(img_path)
        if img is None:
            print(f"[ERROR] 이미지를 읽을 수 없습니다: {img_path}")
            return
        
        # 예측
        print("[INFO] 기물 인식 중...")
        grid = detect_pieces_ml(img, model_path)
        
        if grid is None:
            print("[ERROR] 예측 실패")
            return
        
        # 결과 출력
        print("\n[예측 결과] (0=empty, 1=white, 2=black)")
        print("   ", " ".join([str(i) for i in range(1, 9)]))
        files = "abcdefgh"
        for r in range(8):
            row_str = f"{files[r]} "
            for c in range(8):
                row_str += f"{grid[r, c]} "
            print(row_str)
        
        # 시각화
        vis = img.copy()
        H, W = vis.shape[:2]
        cell_h, cell_w = H // 8, W // 8
        
        for r in range(8):
            for c in range(8):
                pred = grid[r, c]
                x0, y0 = c * cell_w, r * cell_h
                x1, y1 = (c + 1) * cell_w, (r + 1) * cell_h
                
                if pred == 1:  # white
                    cv2.rectangle(vis, (x0, y0), (x1, y1), (255, 255, 255), 2)
                    cv2.putText(vis, "W", (x0 + 5, y0 + 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                elif pred == 2:  # black
                    cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 0, 0), 2)
                    cv2.putText(vis, "B", (x0 + 5, y0 + 20), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        
        cv2.imshow("ML Piece Detection", vis)
        print("\n[INFO] 이미지를 표시합니다. 아무 키나 누르면 종료합니다.")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

