# -*- coding: utf-8 -*-
"""
머신러닝 기반 체스 기물 인식 모듈
Colab에서 학습한 ResNet18 모델을 사용하여 체스판 이미지에서 기물을 인식합니다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

try:
    import torch
    import torch.nn as nn
    import torchvision
    import torchvision.transforms as T
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[WARNING] PyTorch가 설치되지 않았습니다. ML 기물 인식 기능을 사용할 수 없습니다.")


class ChessPieceMLDetector:
    """머신러닝 기반 체스 기물 인식기"""
    
    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        """
        Args:
            model_path: 학습된 모델 가중치 파일 경로 (.pt 파일)
            device: 사용할 디바이스 ('cuda' 또는 'cpu'). None이면 자동 선택
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch가 필요합니다. pip install torch torchvision")
        
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.model_path = model_path
        
        # 이미지 전처리 변환 (추론용)
        self.infer_transform = T.Compose([
            T.ToPILImage(),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str) -> bool:
        """
        학습된 모델 가중치를 로드합니다.
        
        Args:
            model_path: 모델 가중치 파일 경로
            
        Returns:
            로드 성공 여부
        """
        if not os.path.exists(model_path):
            print(f"[ERROR] 모델 파일을 찾을 수 없습니다: {model_path}")
            return False
        
        try:
            # ResNet18 모델 생성 (3-class: 0=empty, 1=white, 2=black)
            self.model = torchvision.models.resnet18(weights=None)
            self.model.fc = nn.Linear(self.model.fc.in_features, 3)
            self.model = self.model.to(self.device)
            
            # 가중치 로드
            self.model.load_state_dict(torch.load(model_path, map_location=self.device))
            self.model.eval()
            self.model_path = model_path
            print(f"[✓] ML 모델 로드 완료: {model_path} (device: {self.device})")
            return True
        except Exception as e:
            print(f"[ERROR] 모델 로드 실패: {e}")
            return False
    
    def predict_frame(self, img_bgr: np.ndarray, target_size: Tuple[int, int] = (640, 480)) -> np.ndarray:
        """
        체스판 이미지에서 각 칸의 기물을 예측합니다.
        
        Args:
            img_bgr: BGR 형식의 체스판 이미지 (OpenCV 형식)
            target_size: 이미지를 리사이즈할 크기 (width, height)
            
        Returns:
            8x8 numpy 배열 (0=empty, 1=white, 2=black)
            - row: rank 8~1 (0=rank 8, 7=rank 1)
            - col: file a~h (0=file a, 7=file h)
            즉, grid[0, 0] = a8, grid[0, 7] = h8, grid[7, 0] = a1, grid[7, 7] = h1
        """
        if self.model is None:
            raise RuntimeError("모델이 로드되지 않았습니다. load_model()을 먼저 호출하세요.")
        
        # 이미지 리사이즈
        img_resized = cv2.resize(img_bgr, target_size, interpolation=cv2.INTER_AREA)
        H, W = img_resized.shape[:2]
        cell_h, cell_w = H // 8, W // 8
        
        # 각 칸을 추출하여 배치로 만들기
        cells = []
        coords = []
        
        for r in range(8):  # a~h (위에서 아래)
            for c in range(8):  # 1~8 (왼쪽에서 오른쪽)
                y0, y1 = r * cell_h, (r + 1) * cell_h
                x0, x1 = c * cell_w, (c + 1) * cell_w
                
                cell = img_resized[y0:y1, x0:x1]
                cell = cv2.resize(cell, (64, 64), interpolation=cv2.INTER_AREA)
                cell = cv2.cvtColor(cell, cv2.COLOR_BGR2RGB)
                
                # 전처리 적용
                x = self.infer_transform(cell)
                cells.append(x)
                coords.append((r, c))
        
        # 배치로 변환하여 예측
        batch = torch.stack(cells, dim=0).to(self.device)  # (64, 3, 64, 64)
        
        with torch.no_grad():
            preds = self.model(batch).argmax(dim=1).cpu().numpy()
        
        # 8x8 그리드로 변환
        grid = np.zeros((8, 8), dtype=int)
        for (r, c), pred in zip(coords, preds):
            grid[r, c] = int(pred)
        
        # 좌표 변환:
        # - 이미지: img[r][c]는 위에서 아래(r=0~7), 왼쪽에서 오른쪽(c=0~7)
        # - 체스 좌표: grid[chess_r][chess_c]
        #   - chess_r: rank 8~1 (0=rank 8, 7=rank 1)  
        #   - chess_c: file a~h (0=file a, 7=file h)
        #
        # dataset_collector의 CSV 형식:
        # - labels[r][c]: row=file(a~h), col=rank(1~8)
        # - labels[0][0] = a1, labels[0][7] = a8
        # - labels[7][0] = h1, labels[7][7] = h8
        #
        # 변환 공식:
        # - labels[r][c] = (file=a+r, rank=c+1)
        # - chess_grid[8-rank][file] = chess_grid[8-(c+1)][r] = chess_grid[7-c][r]
        # - 즉: chess_grid[7-c][r] = labels[r][c]
        #
        # 그런데 이미지를 읽을 때 카메라가 rotate_180=True로 설정되어 있으므로
        # 이미지가 이미 180도 회전된 상태입니다.
        # 따라서: img[r][c] → labels[r][c] (동일 좌표)
        
        corrected_grid = np.zeros((8, 8), dtype=int)
        for r in range(8):  
            for c in range(8):  
                # labels[r][c] → chess_grid[7-c][r]
                corrected_grid[7 - c, r] = grid[r, c]
        
        return corrected_grid
    
    def print_grid(self, grid: np.ndarray, title: str = "ML 예측 결과") -> None:
        """
        ML 예측 결과를 콘솔에 보기 좋게 출력합니다.
        
        Args:
            grid: 8x8 numpy 배열 (0=empty, 1=white, 2=black)
            title: 출력 제목
            
        좌표 체계: grid[r][c]는 체스 좌표 (file=a+c, rank=8-r)
        - grid[0][0] = a8 (왼쪽 위)
        - grid[0][7] = h8 (오른쪽 위)
        - grid[7][0] = a1 (왼쪽 아래)
        - grid[7][7] = h1 (오른쪽 아래)
        """
        print(f"\n[{title}]")
        # 열 헤더: a b c d e f g h
        print("  " + " ".join(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']))
        
        for r in range(8):
            rank = 8 - r  # row 0 = rank 8, row 7 = rank 1
            row_str = f"{rank} "
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
        print()
    
    def predict_from_capture(self, capture, target_size: Tuple[int, int] = (640, 480)) -> Optional[np.ndarray]:
        """
        캡처 객체에서 프레임을 읽어 기물을 예측합니다.
        
        Args:
            capture: OpenCV VideoCapture 객체 또는 ThreadSafeCapture 래퍼
            target_size: 이미지를 리사이즈할 크기
            
        Returns:
            8x8 numpy 배열 또는 None (프레임 읽기 실패 시)
        """
        try:
            # ThreadSafeCapture와 일반 VideoCapture 모두 read() 메서드를 가지고 있음
            ret, frame = capture.read()
            
            if not ret or frame is None:
                print("[ERROR] 프레임을 읽을 수 없습니다.")
                return None
            
            return self.predict_frame(frame, target_size)
        except Exception as e:
            print(f"[ERROR] 프레임 읽기 중 오류 발생: {e}")
            return None


# 전역 인스턴스 (선택적)
_global_detector: Optional[ChessPieceMLDetector] = None


def get_ml_detector(model_path: Optional[str] = None, device: Optional[str] = None) -> Optional[ChessPieceMLDetector]:
    """
    전역 ML 기물 인식기 인스턴스를 가져오거나 생성합니다.
    
    Args:
        model_path: 모델 파일 경로 (None이면 기존 인스턴스 반환)
        device: 사용할 디바이스
        
    Returns:
        ChessPieceMLDetector 인스턴스 또는 None (PyTorch 미설치 시)
    """
    global _global_detector
    
    if not TORCH_AVAILABLE:
        return None
    
    if _global_detector is None and model_path:
        _global_detector = ChessPieceMLDetector(model_path, device)
    elif _global_detector is None:
        print("[WARNING] 모델 경로가 제공되지 않았습니다.")
    
    return _global_detector


def detect_pieces_ml(
    img_bgr: np.ndarray,
    model_path: str,
    target_size: Tuple[int, int] = (640, 480),
    device: Optional[str] = None
) -> Optional[np.ndarray]:
    """
    편의 함수: 이미지에서 기물을 예측합니다.
    
    Args:
        img_bgr: BGR 형식의 체스판 이미지
        model_path: 모델 파일 경로
        target_size: 리사이즈 크기
        device: 사용할 디바이스
        
    Returns:
        8x8 numpy 배열 (0=empty, 1=white, 2=black) 또는 None
    """
    try:
        detector = ChessPieceMLDetector(model_path, device)
        return detector.predict_frame(img_bgr, target_size)
    except Exception as e:
        print(f"[ERROR] ML 기물 인식 실패: {e}")
        return None

