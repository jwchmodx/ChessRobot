#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
기존 이미지와 라벨로 ML 모델 학습하는 스크립트
"""

import sys
import os
from pathlib import Path

# brain 모듈 경로 추가
aicv_dir = Path(__file__).parent
brain_dir = aicv_dir.parent
sys.path.insert(0, str(brain_dir))

# aicv 모듈 경로도 추가
sys.path.insert(0, str(aicv_dir))

from ml_trainer import train_model


def main():
    """메인 함수"""
    # 경로 설정
    base_dir = Path(__file__).parent
    images_dir = str(base_dir / "images")
    labels_dir = str(base_dir / "labels")
    output_path = str(base_dir / "models" / "chess_piece_model.pt")
    
    # 출력 디렉토리 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print("=" * 60)
    print("체스 기물 인식 ML 모델 학습")
    print("=" * 60)
    print(f"이미지 디렉토리: {images_dir}")
    print(f"라벨 디렉토리: {labels_dir}")
    print(f"출력 모델: {output_path}")
    print("=" * 60)
    
    # 이미지 파일 개수 확인
    image_files = sorted([
        f for f in Path(images_dir).iterdir()
        if f.is_file() and f.suffix.lower() in {'.png', '.jpg', '.jpeg'}
        and f.stem.startswith('frame')
    ])
    
    if len(image_files) == 0:
        print(f"[ERROR] frame 형식의 이미지 파일을 찾을 수 없습니다: {images_dir}")
        return 1
    
    print(f"[INFO] {len(image_files)}개의 이미지 파일을 찾았습니다.")
    
    # 라벨 파일 개수 확인
    label_files = sorted([
        f for f in Path(labels_dir).iterdir()
        if f.is_file() and f.suffix == '.csv' and f.stem.startswith('frame')
    ])
    
    if len(label_files) == 0:
        print(f"[ERROR] frame 형식의 라벨 파일을 찾을 수 없습니다: {labels_dir}")
        return 1
    
    print(f"[INFO] {len(label_files)}개의 라벨 파일을 찾았습니다.")
    
    # 프레임 번호 추출
    frame_indices = []
    for img_file in image_files:
        try:
            # frame01.png -> 1
            idx_str = img_file.stem.replace('frame', '')
            idx = int(idx_str)
            # 라벨 파일도 있는지 확인
            label_path = Path(labels_dir) / f"frame{idx:02d}.csv"
            if label_path.exists():
                frame_indices.append(idx)
            else:
                print(f"[WARNING] 프레임 {idx:02d}의 라벨 파일이 없습니다. 제외됩니다.")
        except:
            continue
    
    if len(frame_indices) == 0:
        print("[ERROR] 유효한 프레임 번호를 찾을 수 없습니다.")
        return 1
    
    frame_indices = sorted(frame_indices)
    print(f"[INFO] 사용 가능한 프레임: {frame_indices[0]} ~ {frame_indices[-1]} ({len(frame_indices)}개)")
    
    # 사용자에게 프레임 선택 방식 물어보기
    print("\n프레임 선택 방식:")
    print("  1. 자동 분할 (80% 학습, 20% 검증)")
    print("  2. 수동 선택 (학습/검증 프레임 직접 지정)")
    choice = input("선택 (1 또는 2, 기본값: 1): ").strip()
    
    if choice == "2":
        # 수동 선택 모드
        print(f"\n사용 가능한 프레임: {frame_indices}")
        print("\n학습용 프레임을 입력하세요.")
        print("  예시: 1-30 또는 1,2,3,5,10-15")
        train_input = input("학습 프레임: ").strip()
        
        print("\n검증용 프레임을 입력하세요.")
        print("  예시: 31-35 또는 31,32,33")
        val_input = input("검증 프레임: ").strip()
        
        # 프레임 번호 파싱
        def parse_frames(input_str: str) -> list[int]:
            frames = []
            for part in input_str.split(','):
                part = part.strip()
                if '-' in part:
                    start, end = map(int, part.split('-'))
                    frames.extend(range(start, end + 1))
                else:
                    frames.append(int(part))
            return sorted(set(frames))
        
        try:
            train_frames = parse_frames(train_input)
            val_frames = parse_frames(val_input)
            
            # 유효성 검사
            all_selected = set(train_frames + val_frames)
            available_set = set(frame_indices)
            invalid = all_selected - available_set
            
            if invalid:
                print(f"[ERROR] 존재하지 않는 프레임: {sorted(invalid)}")
                return 1
            
            if len(train_frames) == 0:
                print("[ERROR] 학습 프레임이 없습니다.")
                return 1
            
            if len(val_frames) == 0:
                print("[ERROR] 검증 프레임이 없습니다.")
                return 1
            
            print(f"\n[INFO] 학습 프레임: {train_frames} ({len(train_frames)}개)")
            print(f"[INFO] 검증 프레임: {val_frames} ({len(val_frames)}개)")
            
        except Exception as e:
            print(f"[ERROR] 프레임 파싱 실패: {e}")
            return 1
    else:
        # 자동 분할 모드 (기본값)
        print(f"[INFO] 전체 데이터셋을 사용하여 자동 분할합니다.")
        
        # 학습/검증 분할 (80% 학습, 20% 검증)
        split_idx = int(len(frame_indices) * 0.8)
        train_frames = frame_indices[:split_idx]
        val_frames = frame_indices[split_idx:]
        
        if len(val_frames) == 0:
            # 검증 데이터가 없으면 마지막 2개를 검증용으로
            if len(train_frames) >= 2:
                val_frames = train_frames[-2:]
                train_frames = train_frames[:-2]
            else:
                print("[ERROR] 검증 데이터가 부족합니다. 최소 3개 이상의 프레임이 필요합니다.")
                return 1
        
        print(f"[INFO] 학습 프레임: {train_frames[0]} ~ {train_frames[-1]} ({len(train_frames)}개)")
        print(f"[INFO] 검증 프레임: {val_frames[0]} ~ {val_frames[-1]} ({len(val_frames)}개)")
    
    # 기존 모델 경로 확인 (추가 학습용)
    base_model_path = None
    if os.path.exists(output_path):
        print(f"\n[INFO] 기존 모델 파일이 발견되었습니다: {output_path}")
        response = input("기존 모델에 추가 학습하시겠습니까? (y/n, 기본값: n): ").strip().lower()
        if response == 'y':
            base_model_path = output_path
            print("[INFO] 추가 학습 모드로 진행합니다.")
        else:
            print("[INFO] 처음부터 새로 학습합니다.")
    
    # 사용자 확인
    print("\n학습 설정:")
    print(f"  - 모드: {'추가 학습' if base_model_path else '처음부터 학습'}")
    print(f"  - 에포크: 12")
    print(f"  - 배치 크기: 128")
    print(f"  - 학습률: 3e-4")
    response = input("\n학습을 시작하시겠습니까? (y/n): ").strip().lower()
    if response != 'y':
        print("학습이 취소되었습니다.")
        return 0
    
    try:
        best_acc, model_path, test_acc = train_model(
            img_dir=images_dir,
            label_dir=labels_dir,
            train_frames=train_frames,
            val_frames=val_frames,
            output_path=output_path,
            base_model_path=base_model_path,  # 기존 모델 경로 (None이면 처음부터 학습)
            epochs=12,
            batch_size=128,
            learning_rate=3e-4,
            device=None,  # 자동 선택 (CUDA 있으면 GPU, 없으면 CPU)
            num_workers=2,
        )
        
        print("\n" + "=" * 60)
        print(f"[✓] 학습 완료!")
        print(f"최고 검증 정확도 (학습 중): {best_acc:.4f}")
        print(f"최종 테스트 정확도 (검증 데이터셋): {test_acc:.4f}")
        print(f"모델 저장 경로: {model_path}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] 학습 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

