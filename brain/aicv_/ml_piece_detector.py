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
            - row: a~h (0=a, 7=h)
            - col: 1~8 (0=1, 7=8)
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
        
        return grid
    
    def predict_from_capture(self, capture, target_size: Tuple[int, int] = (640, 480)) -> Optional[np.ndarray]:
        """
        캡처 객체에서 프레임을 읽어 기물을 예측합니다.
        
        Args:
            capture: OpenCV VideoCapture 객체 또는 ThreadSafeCapture 래퍼
            target_size: 이미지를 리사이즈할 크기
            
        Returns:
            8x8 numpy 배열 또는 None (프레임 읽기 실패 시)
        """
        # ThreadSafeCapture 래퍼인 경우
        if hasattr(capture, 'read'):
            ret, frame = capture.read()
        else:
            # 일반 VideoCapture인 경우
            ret, frame = capture.read()
        
        if not ret or frame is None:
            print("[ERROR] 프레임을 읽을 수 없습니다.")
            return None
        
        return self.predict_frame(frame, target_size)


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

