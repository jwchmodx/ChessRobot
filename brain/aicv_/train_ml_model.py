#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ML 체스 기물 인식 모델 학습 스크립트
추가 학습 및 재학습을 위한 CLI 도구
"""

import sys
import os
import argparse
from pathlib import Path

# brain 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "brain"))

from cv.ml_trainer import train_model, check_labels_exist


def main():
    parser = argparse.ArgumentParser(description="체스 기물 인식 ML 모델 학습")
    parser.add_argument("--img-dir", type=str, required=True,
                       help="이미지 디렉토리 경로")
    parser.add_argument("--label-dir", type=str, required=True,
                       help="라벨 CSV 디렉토리 경로")
    parser.add_argument("--train-frames", type=str, required=True,
                       help="학습용 프레임 번호 (예: '1-28' 또는 '1,2,3,4')")
    parser.add_argument("--val-frames", type=str, required=True,
                       help="검증용 프레임 번호 (예: '29-30' 또는 '29,30')")
    parser.add_argument("--output", type=str, required=True,
                       help="저장할 모델 파일 경로 (.pt)")
    parser.add_argument("--base-model", type=str, default=None,
                       help="기존 모델 경로 (추가 학습 시 사용)")
    parser.add_argument("--epochs", type=int, default=12,
                       help="학습 에포크 수 (기본값: 12)")
    parser.add_argument("--batch-size", type=int, default=128,
                       help="배치 크기 (기본값: 128)")
    parser.add_argument("--lr", type=float, default=3e-4,
                       help="학습률 (기본값: 3e-4)")
    parser.add_argument("--device", type=str, default=None,
                       help="사용할 디바이스 ('cuda' 또는 'cpu', 기본값: 자동)")
    parser.add_argument("--num-workers", type=int, default=2,
                       help="DataLoader 워커 수 (기본값: 2)")
    
    args = parser.parse_args()
    
    # 프레임 번호 파싱
    def parse_frames(frame_str: str) -> list:
        """프레임 번호 문자열을 리스트로 변환 (예: '1-28' 또는 '1,2,3')"""
        if '-' in frame_str:
            # 범위 형식 (예: '1-28')
            start, end = map(int, frame_str.split('-'))
            return list(range(start, end + 1))
        else:
            # 쉼표 구분 형식 (예: '1,2,3')
            return [int(x.strip()) for x in frame_str.split(',')]
    
    train_frames = parse_frames(args.train_frames)
    val_frames = parse_frames(args.val_frames)
    
    print("=" * 60)
    print("체스 기물 인식 ML 모델 학습")
    print("=" * 60)
    print(f"이미지 디렉토리: {args.img_dir}")
    print(f"라벨 디렉토리: {args.label_dir}")
    print(f"학습 프레임: {train_frames}")
    print(f"검증 프레임: {val_frames}")
    print(f"출력 모델: {args.output}")
    if args.base_model:
        print(f"기존 모델 (추가 학습): {args.base_model}")
    print(f"에포크: {args.epochs}, 배치 크기: {args.batch_size}, 학습률: {args.lr}")
    print("=" * 60)
    
    # 디렉토리 확인
    if not os.path.exists(args.img_dir):
        print(f"[ERROR] 이미지 디렉토리가 없습니다: {args.img_dir}")
        return 1
    
    if not os.path.exists(args.label_dir):
        print(f"[ERROR] 라벨 디렉토리가 없습니다: {args.label_dir}")
        return 1
    
    # 출력 디렉토리 생성
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        print(f"[INFO] 출력 디렉토리 생성: {output_dir}")
    
    try:
        best_acc, model_path = train_model(
            img_dir=args.img_dir,
            label_dir=args.label_dir,
            train_frames=train_frames,
            val_frames=val_frames,
            output_path=args.output,
            base_model_path=args.base_model,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            device=args.device,
            num_workers=args.num_workers,
        )
        
        print("\n" + "=" * 60)
        print(f"[✓] 학습 완료!")
        print(f"최고 검증 정확도: {best_acc:.4f}")
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

