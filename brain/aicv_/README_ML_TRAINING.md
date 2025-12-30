# ML 체스 기물 인식 모델 학습 가이드

## 개요

이 도구는 ResNet18 기반의 체스 기물 인식 모델을 학습하고 추가 학습(fine-tuning)을 수행할 수 있습니다.

## 데이터 준비

### 1. 이미지 파일
- 체스판 이미지를 `frame01.jpg`, `frame02.jpg`, ... 형식으로 저장
- 이미지 크기는 자동으로 640x480으로 리사이즈됩니다

### 2. 라벨 CSV 파일
각 프레임에 대해 `frame01.csv`, `frame02.csv`, ... 형식의 라벨 파일이 필요합니다.

CSV 형식:
```csv
,1,2,3,4,5,6,7,8
a,0,0,0,0,0,0,0,0
b,0,0,0,0,0,0,0,0
c,0,0,0,0,0,0,0,0
d,0,0,0,0,0,0,0,0
e,0,0,0,0,0,0,0,0
f,0,0,0,0,0,0,0,0
g,0,0,0,0,0,0,0,0
h,0,0,0,0,0,0,0,0
```

라벨 값:
- `0`: 빈 칸 (empty)
- `1`: 흰색 기물 (white)
- `2`: 검은색 기물 (black)

## 사용 방법

### 처음부터 학습하기

```bash
python3 tools/train_ml_model.py \
    --img-dir /path/to/images \
    --label-dir /path/to/labels \
    --train-frames "1-28" \
    --val-frames "29-30" \
    --output /path/to/model.pt \
    --epochs 12 \
    --batch-size 128
```

### 기존 모델에 추가 학습하기

```bash
python3 tools/train_ml_model.py \
    --img-dir /path/to/new_images \
    --label-dir /path/to/new_labels \
    --train-frames "31-40" \
    --val-frames "41-42" \
    --output /path/to/updated_model.pt \
    --base-model /path/to/existing_model.pt \
    --epochs 10 \
    --batch-size 128
```

### 프레임 번호 지정 방법

**범위 형식:**
```bash
--train-frames "1-28"    # 1부터 28까지
--val-frames "29-30"     # 29, 30
```

**쉼표 구분 형식:**
```bash
--train-frames "1,2,3,5,7,10"    # 특정 프레임만
--val-frames "29,30"             # 29, 30
```

## 파라미터 설명

- `--img-dir`: 이미지 파일이 있는 디렉토리
- `--label-dir`: 라벨 CSV 파일이 있는 디렉토리
- `--train-frames`: 학습용 프레임 번호 (범위 또는 쉼표 구분)
- `--val-frames`: 검증용 프레임 번호
- `--output`: 저장할 모델 파일 경로 (.pt)
- `--base-model`: (선택) 기존 모델 경로 (추가 학습 시)
- `--epochs`: 학습 에포크 수 (기본값: 12)
- `--batch-size`: 배치 크기 (기본값: 128)
- `--lr`: 학습률 (기본값: 3e-4)
- `--device`: 사용할 디바이스 ('cuda' 또는 'cpu', 기본값: 자동)
- `--num-workers`: DataLoader 워커 수 (기본값: 2)

## 예제

### 예제 1: 처음부터 학습
```bash
python3 tools/train_ml_model.py \
    --img-dir ~/chess_data/images \
    --label-dir ~/chess_data/labels \
    --train-frames "1-25" \
    --val-frames "26-30" \
    --output ~/chess_models/best_model.pt \
    --epochs 15
```

### 예제 2: 추가 학습
```bash
python3 tools/train_ml_model.py \
    --img-dir ~/chess_data/new_images \
    --label-dir ~/chess_data/new_labels \
    --train-frames "31-45" \
    --val-frames "46-50" \
    --output ~/chess_models/updated_model.pt \
    --base-model ~/chess_models/best_model.pt \
    --epochs 10 \
    --lr 1e-4
```

## Python 코드에서 직접 사용

```python
from cv.ml_trainer import train_model

# 처음부터 학습
best_acc, model_path = train_model(
    img_dir="/path/to/images",
    label_dir="/path/to/labels",
    train_frames=list(range(1, 29)),
    val_frames=[29, 30],
    output_path="/path/to/model.pt",
    epochs=12,
)

# 추가 학습
best_acc, model_path = train_model(
    img_dir="/path/to/new_images",
    label_dir="/path/to/new_labels",
    train_frames=list(range(31, 41)),
    val_frames=[41, 42],
    output_path="/path/to/updated_model.pt",
    base_model_path="/path/to/existing_model.pt",
    epochs=10,
)
```

## 주의사항

1. **데이터 형식**: 이미지와 라벨 파일의 프레임 번호가 일치해야 합니다.
2. **GPU 사용**: CUDA가 가능하면 자동으로 GPU를 사용합니다.
3. **메모리**: 배치 크기가 크면 GPU 메모리가 부족할 수 있습니다.
4. **라벨 누락**: 누락된 라벨 파일은 자동으로 제외됩니다.

