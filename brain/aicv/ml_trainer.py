# -*- coding: utf-8 -*-
"""
머신러닝 체스 기물 인식 모델 학습 모듈
추가 학습 및 재학습을 위한 함수들을 제공합니다.
"""

from __future__ import annotations

import os
import glob
import csv
from pathlib import Path
from typing import List, Tuple, Optional

import cv2
import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    import torchvision
    import torchvision.transforms as T
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[WARNING] PyTorch가 설치되지 않았습니다. ML 학습 기능을 사용할 수 없습니다.")


# 체스 표기법
FILES = list("abcdefgh")
RANKS = [str(i) for i in range(1, 9)]


def find_frame_image(img_dir: str, frame_idx: int) -> Optional[str]:
    """
    프레임 번호에 해당하는 이미지 파일을 찾습니다.
    
    Args:
        img_dir: 이미지 디렉토리 경로
        frame_idx: 프레임 번호 (1부터 시작)
        
    Returns:
        이미지 파일 경로 또는 None
    """
    key = f"frame{frame_idx:02d}"
    candidates = sorted(glob.glob(os.path.join(img_dir, key + ".*")))
    if len(candidates) == 0:
        return None
    return candidates[0]


def load_label_csv(label_dir: str, frame_idx: int) -> Optional[np.ndarray]:
    """
    CSV 파일에서 라벨을 로드합니다.
    
    Args:
        label_dir: 라벨 CSV 디렉토리 경로
        frame_idx: 프레임 번호
        
    Returns:
        8x8 numpy 배열 (0=empty, 1=white, 2=black) 또는 None
    """
    path = os.path.join(label_dir, f"frame{frame_idx:02d}.csv")
    if not os.path.exists(path):
        return None
    
    try:
        df = pd.read_csv(path)
        arr = df.iloc[:, 1:].astype(int).values  # 첫 열(file) 제외
        if arr.shape != (8, 8):
            return None
        return arr
    except Exception as e:
        print(f"[ERROR] 라벨 로드 실패 {path}: {e}")
        return None


def save_label_csv(arr_8x8: np.ndarray, out_path: str):
    """
    라벨을 CSV 파일로 저장합니다.
    
    Args:
        arr_8x8: 8x8 numpy 배열 (0=empty, 1=white, 2=black)
        out_path: 저장할 파일 경로
    """
    df = pd.DataFrame(arr_8x8, columns=RANKS)
    df.insert(0, "", FILES)  # 첫 열에 a~h
    df.to_csv(out_path, index=False)


def check_labels_exist(label_dir: str, frame_indices: List[int]) -> List[int]:
    """
    누락된 라벨 파일을 확인합니다.
    
    Args:
        label_dir: 라벨 디렉토리 경로
        frame_indices: 확인할 프레임 번호 리스트
        
    Returns:
        누락된 프레임 번호 리스트
    """
    missing = []
    for fi in frame_indices:
        path = os.path.join(label_dir, f"frame{fi:02d}.csv")
        if not os.path.exists(path):
            missing.append(fi)
    return missing


class ChessCellDataset(Dataset):
    """체스 칸 단위 데이터셋 (3-class: 0=empty, 1=white, 2=black)"""
    
    def __init__(self, img_dir: str, label_dir: str, frame_indices: List[int], train: bool = True):
        """
        Args:
            img_dir: 이미지 디렉토리 경로
            label_dir: 라벨 CSV 디렉토리 경로
            frame_indices: 사용할 프레임 번호 리스트
            train: 학습용 여부 (True면 augmentation 적용)
        """
        self.img_dir = img_dir
        self.label_dir = label_dir
        self.samples = []  # (img_path, r, c, label)
        self.train = train
        
        for fi in frame_indices:
            img_path = find_frame_image(img_dir, fi)
            if img_path is None:
                print(f"[WARNING] 프레임 {fi:02d} 이미지를 찾을 수 없습니다.")
                continue
            
            lab = load_label_csv(label_dir, fi)
            if lab is None:
                print(f"[WARNING] 프레임 {fi:02d} 라벨을 찾을 수 없습니다.")
                continue
            
            for r in range(8):  # a~h (위에서 아래)
                for c in range(8):  # 1~8 (왼쪽에서 오른쪽)
                    self.samples.append((img_path, r, c, int(lab[r, c])))
        
        # 전처리 변환
        if train:
            self.tf = T.Compose([
                T.ToPILImage(),
                T.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.05, hue=0.02),
                T.RandomAffine(degrees=3, translate=(0.02, 0.02), scale=(0.98, 1.02)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
        else:
            self.tf = T.Compose([
                T.ToPILImage(),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        img_path, r, c, y = self.samples[idx]
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"이미지를 읽을 수 없습니다: {img_path}")
        
        img = cv2.resize(img, (640, 480), interpolation=cv2.INTER_AREA)
        H, W = img.shape[:2]
        ch, cw = H // 8, W // 8
        
        # 해당 칸 추출
        cell = img[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw]
        cell = cv2.resize(cell, (64, 64), interpolation=cv2.INTER_AREA)
        cell = cv2.cvtColor(cell, cv2.COLOR_BGR2RGB)
        
        x = self.tf(cell)
        return x, y


def train_model(
    img_dir: str,
    label_dir: str,
    train_frames: List[int],
    val_frames: List[int],
    output_path: str,
    base_model_path: Optional[str] = None,
    epochs: int = 12,
    batch_size: int = 128,
    learning_rate: float = 3e-4,
    device: Optional[str] = None,
    num_workers: int = 2,
) -> Tuple[float, str]:
    """
    체스 기물 인식 모델을 학습합니다.
    
    Args:
        img_dir: 이미지 디렉토리 경로
        label_dir: 라벨 CSV 디렉토리 경로
        train_frames: 학습용 프레임 번호 리스트
        val_frames: 검증용 프레임 번호 리스트
        output_path: 저장할 모델 파일 경로
        base_model_path: 기존 모델 경로 (None이면 처음부터 학습)
        epochs: 학습 에포크 수
        batch_size: 배치 크기
        learning_rate: 학습률
        device: 사용할 디바이스 ('cuda' 또는 'cpu')
        num_workers: DataLoader 워커 수
        
    Returns:
        (best_accuracy, saved_model_path, test_accuracy) 튜플
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch가 필요합니다. pip install torch torchvision")
    
    device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[INFO] 디바이스: {device}")
    
    # 누락된 라벨 확인
    all_frames = train_frames + val_frames
    missing = check_labels_exist(label_dir, all_frames)
    if missing:
        print(f"[WARNING] 누락된 라벨 파일: {missing}")
        print("[WARNING] 해당 프레임은 학습에서 제외됩니다.")
    
    # 데이터셋 생성
    print(f"[INFO] 학습 데이터셋 생성 중... (프레임: {train_frames})")
    train_ds = ChessCellDataset(img_dir, label_dir, train_frames, train=True)
    print(f"[INFO] 검증 데이터셋 생성 중... (프레임: {val_frames})")
    val_ds = ChessCellDataset(img_dir, label_dir, val_frames, train=False)
    
    print(f"[INFO] 학습 샘플 수: {len(train_ds)}, 검증 샘플 수: {len(val_ds)}")
    
    if len(train_ds) == 0:
        raise ValueError("학습 데이터가 없습니다.")
    if len(val_ds) == 0:
        raise ValueError("검증 데이터가 없습니다.")
    
    # DataLoader 생성
    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True,
        num_workers=num_workers, pin_memory=True if device == "cuda" else False
    )
    val_loader = DataLoader(
        val_ds, batch_size=batch_size, shuffle=False,
        num_workers=num_workers, pin_memory=True if device == "cuda" else False
    )
    
    # 모델 생성
    model = torchvision.models.resnet18(weights=torchvision.models.ResNet18_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, 3)  # 0=empty, 1=white, 2=black
    model = model.to(device)
    
    # 기존 모델이 있으면 로드 (추가 학습)
    if base_model_path and os.path.exists(base_model_path):
        print(f"[INFO] 기존 모델 로드 중: {base_model_path}")
        try:
            model.load_state_dict(torch.load(base_model_path, map_location=device))
            print("[✓] 기존 모델 로드 완료 (추가 학습 모드)")
        except Exception as e:
            print(f"[WARNING] 기존 모델 로드 실패: {e}")
            print("[INFO] 처음부터 학습을 시작합니다.")
    
    # 손실 함수 및 옵티마이저
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    
    # 검증 함수
    def evaluate():
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for x, y in val_loader:
                x, y = x.to(device), y.to(device)
                pred = model(x).argmax(dim=1)
                correct += (pred == y).sum().item()
                total += y.numel()
        return correct / total if total > 0 else 0.0
    
    # 학습 루프
    best_acc = 0.0
    best_model_path = output_path
    
    print(f"\n[INFO] 학습 시작 (에포크: {epochs})")
    print("=" * 50)
    
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        num_batches = 0
        
        print(f"\n[Epoch {epoch:02d}/{epochs:02d}] 학습 시작...")
        
        for batch_idx, (x, y) in enumerate(train_loader, 1):
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            num_batches += 1
            
            # 10배치마다 진행 상황 출력
            if batch_idx % 10 == 0 or batch_idx == len(train_loader):
                current_loss = total_loss / num_batches
                print(f"  배치 {batch_idx}/{len(train_loader)} | 평균 loss: {current_loss:.4f}")
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0.0
        
        print(f"[Epoch {epoch:02d}/{epochs:02d}] 검증 중...")
        acc = evaluate()
        
        print(f"[Epoch {epoch:02d}/{epochs:02d}] 완료 | loss: {avg_loss:.4f} | val acc: {acc:.4f}")
        
        if acc > best_acc:
            best_acc = acc
            torch.save(model.state_dict(), best_model_path)
            print(f"  ✓ 최고 성능 모델 저장: {best_model_path} (acc: {best_acc:.4f})")
        else:
            print(f"  (이전 최고: {best_acc:.4f})")
    
    print("=" * 50)
    print(f"[✓] 학습 완료! 최고 검증 정확도: {best_acc:.4f}")
    print(f"[✓] 모델 저장 경로: {best_model_path}")
    
    # 학습 완료 후 최종 모델로 테스트 수행
    print("\n" + "=" * 50)
    print("[TEST] 최종 모델로 검증 데이터셋 테스트 중...")
    print("=" * 50)
    
    # 최종 모델 로드
    model.load_state_dict(torch.load(best_model_path, map_location=device))
    model.eval()
    
    # 테스트 수행
    test_correct, test_total = 0, 0
    with torch.no_grad():
        for x, y in val_loader:
            x, y = x.to(device), y.to(device)
            pred = model(x).argmax(dim=1)
            test_correct += (pred == y).sum().item()
            test_total += y.numel()
    
    test_acc = test_correct / test_total if test_total > 0 else 0.0
    print(f"[TEST] 최종 테스트 정확도: {test_acc:.4f} ({test_correct}/{test_total})")
    print("=" * 50)
    
    return best_acc, best_model_path, test_acc

