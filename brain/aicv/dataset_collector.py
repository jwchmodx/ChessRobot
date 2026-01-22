#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
체스 기물 데이터셋 수집 웹 인터페이스
카메라로 프레임을 캡처하고 8x8 그리드로 라벨링하여 데이터셋을 생성합니다.
"""

from __future__ import annotations

import os
import sys
import json
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

import cv2
import numpy as np
from flask import Flask, Response, render_template_string, request, jsonify

# brain 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from cv.cv_web import USBCapture, ThreadSafeCapture, _encode_jpeg, _resize_for_preview
from cv.picam_stable import warp_chessboard, find_green_corners

# ML 모델 import (선택적)
try:
    from aicv.ml_piece_detector import ChessPieceMLDetector
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("[WARNING] ML 모델을 사용할 수 없습니다. ml_piece_detector를 확인하세요.")

# 설정
WARP_SIZE = 400

# 수동 와핑을 위한 전역 상태
manual_corners = None

# 체스 표기법
FILES = list("abcdefgh")
RANKS = [str(i) for i in range(1, 9)]


class DatasetCollector:
    """데이터셋 수집 클래스"""
    
    def __init__(self, images_dir: str = "images", labels_dir: str = "labels"):
        self.images_dir = Path(images_dir)
        self.labels_dir = Path(labels_dir)
        self.current_frame_idx = 1
        self.current_labels = None  # 8x8 numpy 배열
        
        # 디렉토리 생성
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.labels_dir.mkdir(parents=True, exist_ok=True)
        
        # 기존 프레임 번호 확인
        self._update_frame_idx()
    
    def _update_frame_idx(self):
        """다음 사용할 프레임 번호를 찾습니다."""
        existing = sorted(self.images_dir.glob("frame*.jpg")) + \
                   sorted(self.images_dir.glob("frame*.png"))
        if existing:
            max_idx = 0
            for f in existing:
                try:
                    idx = int(f.stem.replace("frame", ""))
                    max_idx = max(max_idx, idx)
                except:
                    pass
            self.current_frame_idx = max_idx + 1
        else:
            self.current_frame_idx = 1
    
    def save_frame(self, img: np.ndarray) -> str:
        """현재 프레임을 저장하고 다음 번호로 이동합니다."""
        filename = f"frame{self.current_frame_idx:02d}.jpg"
        path = self.images_dir / filename
        cv2.imwrite(str(path), img)
        self.current_frame_idx += 1
        return filename
    
    def save_labels(self, labels: np.ndarray, frame_idx: int) -> str:
        """라벨을 CSV 파일로 저장합니다."""
        import pandas as pd
        
        filename = f"frame{frame_idx:02d}.csv"
        path = self.labels_dir / filename
        
        # DataFrame 생성 (첫 열에 a~h)
        df = pd.DataFrame(labels, columns=RANKS)
        df.insert(0, "", FILES)
        df.to_csv(path, index=False)
        
        return filename
    
    def load_labels(self, frame_idx: int) -> Optional[np.ndarray]:
        """라벨을 로드합니다."""
        path = self.labels_dir / f"frame{frame_idx:02d}.csv"
        if not path.exists():
            return None
        
        try:
            import pandas as pd
            df = pd.read_csv(path)
            arr = df.iloc[:, 1:].astype(int).values  # 첫 열(file) 제외
            if arr.shape == (8, 8):
                return arr
        except Exception as e:
            print(f"[ERROR] 라벨 로드 실패: {e}")
        return None
    
    def get_next_frame_idx(self) -> int:
        """다음 프레임 번호를 반환합니다."""
        return self.current_frame_idx


def build_dataset_collector_app(
    cap: ThreadSafeCapture,
    collector: DatasetCollector,
    ml_detector: Optional[ChessPieceMLDetector] = None,
    port: int = 5004
) -> Flask:
    """데이터셋 수집 웹 앱을 생성합니다."""
    app = Flask(__name__)
    
    def capture_frame() -> Optional[np.ndarray]:
        """최신 프레임을 캡처합니다. (최적화: 버퍼 비우기 최소화)"""
        try:
            # 버퍼를 비우기 위해 2번만 읽기 (4번 -> 2번으로 감소)
            last_frame = None
            for _ in range(2):
                ret, frame = cap.read()
                if ret and frame is not None:
                    last_frame = frame
            if last_frame is None:
                print("[WARNING] capture_frame: 유효한 프레임을 읽지 못했습니다")
            return last_frame
        except Exception as e:
            print(f"[ERROR] capture_frame 오류: {e}")
            return None
    
    @app.route("/")
    def index():
        """메인 페이지"""
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>체스 데이터셋 수집</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        h1 {
            color: #333;
            margin-top: 0;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.3s;
        }
        .btn-primary {
            background: #007bff;
            color: white;
        }
        .btn-primary:hover {
            background: #0056b3;
        }
        .btn-success {
            background: #28a745;
            color: white;
        }
        .btn-success:hover {
            background: #1e7e34;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-secondary:hover {
            background: #545b62;
        }
        .status {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            font-weight: bold;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
        }
        .video-container {
            display: flex;
            gap: 20px;
            margin: 20px 0;
        }
        .video-box {
            flex: 1;
            min-width: 300px;
        }
        .video-box h3 {
            margin-top: 0;
        }
        img {
            max-width: 100%;
            border: 2px solid #ddd;
            border-radius: 4px;
        }
        .board-container {
            margin-top: 20px;
        }
        .board-grid {
            display: grid;
            grid-template-columns: repeat(9, 1fr);
            gap: 2px;
            max-width: 600px;
            margin: 0 auto;
        }
        .board-cell {
            aspect-ratio: 1;
            border: 2px solid #333;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 14px;
            transition: all 0.2s;
        }
        .board-cell:hover {
            transform: scale(1.1);
            z-index: 10;
        }
        .board-cell.empty {
            background: #f0f0f0;
            color: #666;
        }
        .board-cell.white {
            background: #fff;
            color: #000;
            border-color: #000;
        }
        .board-cell.black {
            background: #000;
            color: #fff;
            border-color: #fff;
        }
        .board-cell.header {
            background: #333;
            color: white;
            cursor: default;
            font-size: 12px;
        }
        .board-cell.header:hover {
            transform: none;
        }
        .label-info {
            margin: 10px 0;
            padding: 10px;
            background: #e9ecef;
            border-radius: 4px;
        }
        .label-info strong {
            color: #495057;
        }
        input[type="number"] {
            padding: 5px;
            width: 80px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>♟️ 체스 데이터셋 수집 도구</h1>
        
        <div class="controls">
            <button class="btn-primary" onclick="captureFrame()">📸 프레임 캡처</button>
            <button class="btn-success" onclick="saveLabels()">💾 라벨 저장</button>
            <button class="btn-secondary" onclick="loadFrame()">📂 프레임 로드</button>
            <button class="btn-danger" onclick="clearLabels()">🗑️ 라벨 초기화</button>
            <button class="btn-secondary" onclick="window.open('/manual', '_blank')">🎯 수동 와핑 설정</button>
        </div>
        
        <div id="status"></div>
        
        <div class="label-info">
            <strong>현재 프레임:</strong> <span id="current-frame">-</span> | 
            <strong>다음 프레임:</strong> <span id="next-frame">-</span> | 
            <strong>라벨 상태:</strong> <span id="label-status">초기화되지 않음</span> | 
            <strong>와핑 모드:</strong> <span id="warp-mode">자동 감지</span> | 
            <strong>ML 모델:</strong> <span id="ml-status">확인 중...</span> | 
            <strong>카메라 상태:</strong> <span id="camera-status">확인 중...</span>
        </div>
        
        <div class="video-container">
            <div class="video-box">
                <h3>원본 카메라</h3>
                <img id="original-img" src="/stream_original" style="width: 100%;" />
            </div>
            <div class="video-box">
                <h3>와핑된 체스판</h3>
                <img id="warped-img" src="/stream_warped" style="width: 100%;" />
            </div>
        </div>
        
        <div class="container board-container">
            <h3>체스판 라벨링 (클릭하여 변경)</h3>
            <p style="color: #666; font-size: 14px;">
                <strong>빈 칸</strong> (클릭 1회) → <strong>흰색</strong> (클릭 2회) → <strong>검은색</strong> (클릭 3회) → <strong>빈 칸</strong> (반복)
            </p>
            <div class="board-grid" id="board-grid"></div>
        </div>
    </div>
    
    <script>
        let currentFrameIdx = 1;
        let labels = Array(8).fill(null).map(() => Array(8).fill(0)); // 0=empty, 1=white, 2=black
        let capturedImage = null;
        
        // 보드 그리드 생성
        function createBoard() {
            const grid = document.getElementById('board-grid');
            grid.innerHTML = '';
            
            // 헤더 행
            const headerRow = document.createElement('div');
            headerRow.className = 'board-cell header';
            headerRow.textContent = '';
            grid.appendChild(headerRow);
            for (let i = 1; i <= 8; i++) {
                const cell = document.createElement('div');
                cell.className = 'board-cell header';
                cell.textContent = i;
                grid.appendChild(cell);
            }
            
            // 체스판 칸들
            const files = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
            for (let r = 0; r < 8; r++) {
                // 파일 라벨
                const fileLabel = document.createElement('div');
                fileLabel.className = 'board-cell header';
                fileLabel.textContent = files[r];
                grid.appendChild(fileLabel);
                
                // 각 칸
                for (let c = 0; c < 8; c++) {
                    const cell = document.createElement('div');
                    cell.className = 'board-cell empty';
                    cell.dataset.row = r;
                    cell.dataset.col = c;
                    cell.textContent = getLabelText(labels[r][c]);
                    cell.onclick = () => toggleLabel(r, c);
                    grid.appendChild(cell);
                }
            }
            updateLabelStatus();
        }
        
        function getLabelText(label) {
            if (label === 1) return 'W';
            if (label === 2) return 'B';
            return '';
        }
        
        function toggleLabel(r, c) {
            labels[r][c] = (labels[r][c] + 1) % 3; // 0→1→2→0
            updateCell(r, c);
            updateLabelStatus();
        }
        
        function updateCell(r, c) {
            const cell = document.querySelector(`[data-row="${r}"][data-col="${c}"]`);
            if (!cell) return;
            
            cell.className = 'board-cell';
            const label = labels[r][c];
            if (label === 1) {
                cell.className += ' white';
                cell.textContent = 'W';
            } else if (label === 2) {
                cell.className += ' black';
                cell.textContent = 'B';
            } else {
                cell.className += ' empty';
                cell.textContent = '';
            }
        }
        
        function updateLabelStatus() {
            const empty = labels.flat().filter(l => l === 0).length;
            const white = labels.flat().filter(l => l === 1).length;
            const black = labels.flat().filter(l => l === 2).length;
            document.getElementById('label-status').textContent = 
                `빈 칸: ${empty}, 흰색: ${white}, 검은색: ${black}`;
        }
        
        function setStatus(msg, type = 'info') {
            const status = document.getElementById('status');
            status.className = 'status ' + type;
            status.textContent = msg;
            setTimeout(() => {
                status.textContent = '';
                status.className = '';
            }, 5000);
        }
        
        async function captureFrame() {
            try {
                const response = await fetch('/capture', { method: 'POST' });
                const data = await response.json();
                if (data.success) {
                    currentFrameIdx = data.frame_idx;
                    capturedImage = data.filename;
                    document.getElementById('current-frame').textContent = currentFrameIdx;
                    document.getElementById('next-frame').textContent = currentFrameIdx + 1;
                    
                    // ML 모델이 예측한 라벨이 있으면 사용, 없으면 초기화
                    if (data.predicted_labels && Array.isArray(data.predicted_labels)) {
                        console.log('[ML] 서버에서 예측된 라벨 수신:', data.predicted_labels);
                        labels = data.predicted_labels;
                        setStatus(`프레임 ${currentFrameIdx} 캡처 완료: ${data.filename} (ML 예측 라벨 자동 적용됨)`, 'success');
                    } else {
                        console.log('[ML] 예측된 라벨이 없습니다. 초기화합니다.');
                        labels = Array(8).fill(null).map(() => Array(8).fill(0));
                        setStatus(`프레임 ${currentFrameIdx} 캡처 완료: ${data.filename}`, 'success');
                    }
                    createBoard();
                } else {
                    setStatus('캡처 실패: ' + data.error, 'error');
                }
            } catch (e) {
                setStatus('오류: ' + e, 'error');
            }
        }
        
        async function saveLabels() {
            if (!capturedImage) {
                setStatus('먼저 프레임을 캡처하세요.', 'error');
                return;
            }
            
            try {
                const response = await fetch('/save_labels', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        frame_idx: currentFrameIdx,
                        labels: labels
                    })
                });
                const data = await response.json();
                if (data.success) {
                    setStatus(`라벨 저장 완료: ${data.filename}`, 'success');
                } else {
                    setStatus('저장 실패: ' + data.error, 'error');
                }
            } catch (e) {
                setStatus('오류: ' + e, 'error');
            }
        }
        
        async function loadFrame() {
            const idx = prompt('로드할 프레임 번호를 입력하세요:', currentFrameIdx);
            if (!idx) return;
            
            try {
                const response = await fetch(`/load_frame?idx=${idx}`);
                const data = await response.json();
                if (data.success) {
                    currentFrameIdx = parseInt(idx);
                    labels = data.labels;
                    capturedImage = data.filename;
                    document.getElementById('current-frame').textContent = currentFrameIdx;
                    document.getElementById('next-frame').textContent = currentFrameIdx + 1;
                    createBoard();
                    setStatus(`프레임 ${idx} 로드 완료`, 'success');
                } else {
                    setStatus('로드 실패: ' + data.error, 'error');
                }
            } catch (e) {
                setStatus('오류: ' + e, 'error');
            }
        }
        
        function clearLabels() {
            if (confirm('라벨을 초기화하시겠습니까?')) {
                labels = Array(8).fill(null).map(() => Array(8).fill(0));
                createBoard();
                setStatus('라벨 초기화 완료', 'info');
            }
        }
        
        // 초기화
        createBoard();
        fetch('/get_next_frame_idx')
            .then(r => r.json())
            .then(data => {
                document.getElementById('next-frame').textContent = data.frame_idx;
            });
        
        // 와핑 모드 확인
        function updateWarpMode() {
            fetch('/get_warp_mode')
                .then(r => r.json())
                .then(data => {
                    const modeEl = document.getElementById('warp-mode');
                    if (data.manual_mode) {
                        modeEl.textContent = '수동 와핑';
                        modeEl.style.color = '#28a745';
                    } else {
                        modeEl.textContent = '자동 감지';
                        modeEl.style.color = '#6c757d';
                    }
                })
                .catch(e => console.error('와핑 모드 확인 실패:', e));
        }
        
        // ML 모델 상태 확인
        function updateMLStatus() {
            fetch('/get_ml_status')
                .then(r => r.json())
                .then(data => {
                    const mlEl = document.getElementById('ml-status');
                    if (data.enabled) {
                        mlEl.textContent = '활성화됨';
                        mlEl.style.color = '#28a745';
                    } else {
                        mlEl.textContent = '비활성화됨';
                        mlEl.style.color = '#6c757d';
                    }
                })
                .catch(e => {
                    console.error('ML 상태 확인 실패:', e);
                    document.getElementById('ml-status').textContent = '확인 실패';
                });
        }
        
        // 스트림 갱신 (이미지 로드 완료 후에만 다음 프레임 요청)
        let originalLoading = false;
        let warpedLoading = false;
        
        function updateStreams() {
            const ts = Date.now();
            const originalImg = document.getElementById('original-img');
            const warpedImg = document.getElementById('warped-img');
            
            // 이미지가 로드 중이 아니고 완료된 경우에만 업데이트
            if (originalImg && !originalLoading && originalImg.complete) {
                originalLoading = true;
                originalImg.src = `/stream_original?ts=${ts}`;
            }
            
            if (warpedImg && !warpedLoading && warpedImg.complete) {
                warpedLoading = true;
                warpedImg.src = `/stream_warped?ts=${ts}`;
            }
        }
        
        // 이미지 로드 완료 처리
        document.getElementById('original-img').addEventListener('load', function() {
            originalLoading = false;
        });
        
        document.getElementById('warped-img').addEventListener('load', function() {
            warpedLoading = false;
        });
        
        // 이미지 로드 오류 처리
        document.getElementById('original-img').addEventListener('error', function() {
            console.error('원본 스트림 로드 실패');
            originalLoading = false;
            this.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360"><text x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="red">카메라 오류</text></svg>';
        });
        
        document.getElementById('warped-img').addEventListener('error', function() {
            console.error('와핑 스트림 로드 실패');
            warpedLoading = false;
            this.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320"><text x="50%25" y="50%25" text-anchor="middle" dy=".3em" fill="red">와핑 오류</text></svg>';
        });
        
        // 주기적 업데이트 (갱신 주기를 더 늘려서 부하 감소)
        setInterval(updateStreams, 300);  // 200ms -> 300ms (더 여유있게)
        setInterval(updateWarpMode, 2000);
        setInterval(updateMLStatus, 3000);
        updateWarpMode();
        updateMLStatus();
        
        // 초기 로드 (약간의 지연 후 시작)
        setTimeout(() => updateStreams(), 100);
    </script>
</body>
</html>
        ''')
    
    @app.route("/stream_original")
    def stream_original():
        """원본 카메라 스트림"""
        frame = capture_frame()
        if frame is None:
            return "카메라 오류", 500
        
        # 해상도와 품질을 더 낮춰서 빠른 로딩
        img = _resize_for_preview(frame, max_width=320)
        jpeg = _encode_jpeg(img, quality=40)
        return Response(jpeg, mimetype="image/jpeg")
    
    @app.route("/stream_warped")
    def stream_warped():
        """와핑된 체스판 스트림"""
        global manual_corners
        frame = capture_frame()
        if frame is None:
            return "카메라 오류", 500
        
        # 수동 와핑 모드 확인
        corners = None
        if manual_corners is not None:
            corners = np.array(manual_corners, dtype=np.float32)
        else:
            # 자동 감지
            corners = find_green_corners(frame.copy()) 
        
        if corners is not None and len(corners) == 4:
            warp = warp_chessboard(frame, corners, size=WARP_SIZE)
            img = _resize_for_preview(warp, max_width=240)
        else:
            img = _resize_for_preview(frame, max_width=240)
            # 코너를 찾을 수 없음을 표시
            cv2.putText(img, "Corners not found", (10, 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
        
        # 해상도와 품질을 더 낮춰서 빠른 로딩
        jpeg = _encode_jpeg(img, quality=40)
        return Response(jpeg, mimetype="image/jpeg")
    
    @app.route("/capture", methods=["POST"])
    def capture():
        """프레임 캡처 및 ML 예측"""
        global manual_corners
        frame = capture_frame()
        if frame is None:
            return jsonify({"success": False, "error": "카메라 프레임을 읽을 수 없습니다"})
        
        # 와핑된 이미지 저장
        corners = None
        if manual_corners is not None:
            corners = np.array(manual_corners, dtype=np.float32)
        else:
            corners = find_green_corners(frame.copy())
        
        if corners is not None and len(corners) == 4:
            warp = warp_chessboard(frame, corners, size=WARP_SIZE)
            filename = collector.save_frame(warp)
            warped_img = warp
        else:
            filename = collector.save_frame(frame)
            warped_img = frame
        
        frame_idx = collector.current_frame_idx - 1
        
        # ML 모델로 라벨 예측
        predicted_labels = None
        if ml_detector is not None:
            try:
                print(f"[ML] 프레임 {frame_idx} 예측 시작...")
                print(f"[ML] 입력 이미지 크기: {warped_img.shape}")
                predicted_labels = ml_detector.predict_frame(warped_img, target_size=(WARP_SIZE, WARP_SIZE))
                empty_count = np.sum(predicted_labels == 0)
                white_count = np.sum(predicted_labels == 1)
                black_count = np.sum(predicted_labels == 2)
                print(f"[ML] 예측 완료: 빈칸={empty_count}, 흰색={white_count}, 검은색={black_count}")
                print(f"[ML] 예측 결과 배열:\n{predicted_labels}")
            except Exception as e:
                import traceback
                print(f"[ML ERROR] 예측 실패: {e}")
                print(f"[ML ERROR] 상세 에러:\n{traceback.format_exc()}")
                predicted_labels = None
        else:
            print(f"[ML] ML 모델이 로드되지 않았습니다. 자동 예측을 건너뜁니다.")
        
        response = {
            "success": True,
            "filename": filename,
            "frame_idx": frame_idx
        }
        
        # 예측된 라벨이 있으면 포함
        if predicted_labels is not None:
            response["predicted_labels"] = predicted_labels.tolist()
        
        return jsonify(response)
    
    @app.route("/save_labels", methods=["POST"])
    def save_labels():
        """라벨 저장"""
        data = request.json
        frame_idx = data.get("frame_idx")
        labels_array = data.get("labels")
        
        if frame_idx is None or labels_array is None:
            return jsonify({"success": False, "error": "파라미터가 올바르지 않습니다"})
        
        try:
            labels_np = np.array(labels_array, dtype=int)
            if labels_np.shape != (8, 8):
                return jsonify({"success": False, "error": "라벨 형식이 올바르지 않습니다 (8x8 필요)"})
            
            filename = collector.save_labels(labels_np, frame_idx)
            return jsonify({"success": True, "filename": filename})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/load_frame")
    def load_frame():
        """프레임 및 라벨 로드"""
        frame_idx = request.args.get("idx", type=int)
        if frame_idx is None:
            return jsonify({"success": False, "error": "프레임 번호가 필요합니다"})
        
        # 이미지 파일 확인
        img_path = collector.images_dir / f"frame{frame_idx:02d}.jpg"
        if not img_path.exists():
            return jsonify({"success": False, "error": f"프레임 {frame_idx:02d} 이미지를 찾을 수 없습니다"})
        
        # 라벨 로드
        labels = collector.load_labels(frame_idx)
        if labels is None:
            labels = np.zeros((8, 8), dtype=int)
        
        return jsonify({
            "success": True,
            "filename": img_path.name,
            "labels": labels.tolist()
        })
    
    @app.route("/get_next_frame_idx")
    def get_next_frame_idx():
        """다음 프레임 번호 반환"""
        return jsonify({"frame_idx": collector.get_next_frame_idx()})
    
    @app.route("/get_warp_mode")
    def get_warp_mode():
        """와핑 모드 확인"""
        global manual_corners
        return jsonify({
            "manual_mode": manual_corners is not None,
            "corners": manual_corners if manual_corners else None
        })
    
    @app.route("/get_ml_status")
    def get_ml_status():
        """ML 모델 상태 확인"""
        return jsonify({
            "enabled": ml_detector is not None
        })
    
    @app.route("/manual")
    def manual_corners_page():
        """수동 와핑 설정 페이지"""
        return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>수동 와핑 설정</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-top: 0;
        }
        .controls {
            margin: 20px 0;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
            margin-bottom: 10px;
        }
        .btn-primary {
            background: #007bff;
            color: white;
        }
        .btn-primary:hover {
            background: #0056b3;
        }
        .btn-success {
            background: #28a745;
            color: white;
        }
        .btn-success:hover {
            background: #1e7e34;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .btn-secondary {
            background: #6c757d;
            color: white;
        }
        .btn-secondary:hover {
            background: #545b62;
        }
        #status {
            margin: 10px 0;
            padding: 10px;
            border-radius: 4px;
            font-weight: bold;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
        }
        #canvas {
            border: 2px solid #ddd;
            border-radius: 4px;
            cursor: crosshair;
            max-width: 100%;
        }
        .info-panel {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .info-panel h3 {
            margin-top: 0;
        }
        .point-list {
            font-family: monospace;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 수동 와핑 설정</h1>
        <p>원본 이미지에서 체스판의 4개 모서리를 클릭하여 선택하세요.</p>
        
        <div class="controls">
            <button class="btn-primary" onclick="loadSnapshot()">🔄 이미지 새로고침</button>
            <button class="btn-success" onclick="sendPoints()">💾 와핑 포인트 저장</button>
            <button class="btn-danger" onclick="clearPoints()">🗑️ 포인트 초기화</button>
            <button class="btn-secondary" onclick="clearServer()">🔄 자동 감지 모드로 전환</button>
        </div>
        
        <div id="status"></div>
        
        <div style="text-align: center; margin: 20px 0;">
            <img id="img" style="display: none;" />
            <canvas id="canvas"></canvas>
        </div>
        
        <div class="info-panel">
            <h3>선택된 포인트 (이미지 좌표)</h3>
            <div id="pts" class="point-list"></div>
            <p style="margin-top: 15px; color: #666;">
                <strong>사용법:</strong><br>
                1. 이미지에서 체스판의 4개 모서리를 순서대로 클릭하세요.<br>
                2. 4개 포인트를 모두 선택한 후 "와핑 포인트 저장" 버튼을 클릭하세요.<br>
                3. 저장 후 메인 페이지로 돌아가면 수동 와핑이 적용됩니다.
            </p>
        </div>
    </div>
    
    <script>
        const img = document.getElementById('img');
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        let points = [];
        let loadingSnapshot = false;
        
        function loadSnapshot(force = false) {
            if (loadingSnapshot && !force) return;
            loadingSnapshot = true;
            img.src = '/snapshot_original?ts=' + Date.now();
        }
        
        img.addEventListener('load', () => {
            loadingSnapshot = false;
            drawImage();
        });
        
        img.addEventListener('error', (e) => {
            loadingSnapshot = false;
            setStatus('스냅샷 로드 실패', 'error');
            console.error('snapshot load error', e);
        });
        
        function drawImage() {
            const w = img.naturalWidth || img.width;
            const h = img.naturalHeight || img.height;
            canvas.width = w;
            canvas.height = h;
            ctx.clearRect(0, 0, w, h);
            ctx.drawImage(img, 0, 0, w, h);
            drawOverlay();
        }
        
        function drawOverlay() {
            for (let i = 0; i < points.length; i++) {
                const p = points[i];
                ctx.beginPath();
                ctx.arc(p.x, p.y, 8, 0, Math.PI * 2);
                ctx.fillStyle = '#00ff00';
                ctx.fill();
                ctx.strokeStyle = '#003300';
                ctx.lineWidth = 2;
                ctx.stroke();
                ctx.fillStyle = '#ffffff';
                ctx.font = 'bold 16px sans-serif';
                ctx.fillText((i + 1).toString(), p.x + 10, p.y - 10);
            }
            if (points.length === 4) {
                ctx.beginPath();
                ctx.moveTo(points[0].x, points[0].y);
                ctx.lineTo(points[1].x, points[1].y);
                ctx.lineTo(points[2].x, points[2].y);
                ctx.lineTo(points[3].x, points[3].y);
                ctx.closePath();
                ctx.strokeStyle = '#ffff00';
                ctx.lineWidth = 3;
                ctx.stroke();
            }
            updatePtsPanel();
        }
        
        function canvasPos(evt) {
            const rect = canvas.getBoundingClientRect();
            // 캔버스의 실제 크기와 표시 크기의 비율 계산
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            
            // 클릭 좌표를 캔버스 좌표계로 변환
            const x = (evt.clientX - rect.left) * scaleX;
            const y = (evt.clientY - rect.top) * scaleY;
            
            return {x, y};
        }
        
        canvas.addEventListener('click', (evt) => {
            if (points.length >= 4) {
                setStatus('이미 4개 포인트를 선택했습니다. 초기화 후 다시 선택하세요.', 'info');
                return;
            }
            const p = canvasPos(evt);
            points.push(p);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            drawOverlay();
            setStatus(`포인트 ${points.length}/4 선택됨`, 'info');
        });
        
        function clearPoints() {
            points = [];
            drawImage();
            setStatus('포인트 초기화 완료', 'info');
        }
        
        function updatePtsPanel() {
            const div = document.getElementById('pts');
            let html = '';
            for (let i = 0; i < points.length; i++) {
                const p = points[i];
                html += `<div>#${i + 1} x: ${Math.round(p.x)}, y: ${Math.round(p.y)}</div>`;
            }
            if (points.length === 0) {
                html = '<div style="color: #999;">포인트가 없습니다.</div>';
            }
            div.innerHTML = html;
        }
        
        function setStatus(msg, type = 'info') {
            const status = document.getElementById('status');
            status.className = 'status ' + type;
            status.textContent = msg;
            setTimeout(() => {
                status.textContent = '';
                status.className = '';
            }, 5000);
        }
        
        async function sendPoints() {
            if (points.length !== 4) {
                setStatus('포인트 4개를 선택하세요', 'error');
                return;
            }
            const pts = points.map(p => [Math.round(p.x), Math.round(p.y)]);
            try {
                const res = await fetch('/set_corners', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({points: pts})
                });
                const j = await res.json();
                if (j.success) {
                    setStatus('저장 성공! 수동 와핑 모드가 활성화되었습니다.', 'success');
                } else {
                    setStatus('저장 실패: ' + (j.error || res.status), 'error');
                }
            } catch (e) {
                setStatus('요청 실패: ' + e, 'error');
            }
        }
        
        async function clearServer() {
            try {
                const res = await fetch('/clear_corners', {method: 'POST'});
                const j = await res.json();
                if (j.success) {
                    setStatus('자동 감지 모드로 전환되었습니다.', 'success');
                } else {
                    setStatus('전환 실패', 'error');
                }
            } catch (e) {
                setStatus('요청 실패: ' + e, 'error');
            }
        }
        
        loadSnapshot(true);
        setInterval(() => loadSnapshot(false), 2000);
    </script>
</body>
</html>
        ''')
    
    @app.route("/set_corners", methods=["POST"])
    def set_corners():
        """수동 와핑 포인트 설정"""
        global manual_corners
        try:
            data = request.json
            points = data.get("points")
            if points is None or len(points) != 4:
                return jsonify({"success": False, "error": "4개의 포인트가 필요합니다"})
            
            # 포인트 검증
            for i, p in enumerate(points):
                if len(p) != 2:
                    return jsonify({"success": False, "error": f"포인트 {i+1} 형식이 올바르지 않습니다"})
            
            manual_corners = points
            print(f"[INFO] 수동 와핑 포인트 저장됨: {manual_corners}")
            return jsonify({
                "success": True, 
                "message": "수동 와핑 포인트가 저장되었습니다",
                "corners": manual_corners
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)})
    
    @app.route("/snapshot_original")
    def snapshot_original():
        """원본 스냅샷 (수동 와핑 페이지용)"""
        frame = capture_frame()
        if frame is None:
            return "카메라 오류", 500
        
        img = _resize_for_preview(frame, max_width=1280)
        jpeg = _encode_jpeg(img, quality=85)
        return Response(jpeg, mimetype="image/jpeg")
    
    @app.route("/clear_corners", methods=["POST"])
    def clear_corners():
        """수동 와핑 모드 해제"""
        global manual_corners
        manual_corners = None
        return jsonify({"success": True, "message": "자동 감지 모드로 전환되었습니다"})
    
    @app.route("/check_camera")
    def check_camera():
        """카메라 연결 상태 확인"""
        try:
            frame = capture_frame()
            if frame is None:
                return jsonify({
                    "connected": False,
                    "error": "프레임을 읽을 수 없습니다"
                })
            
            h, w = frame.shape[:2]
            return jsonify({
                "connected": True,
                "width": w,
                "height": h,
                "message": "카메라 정상 작동 중"
            })
        except Exception as e:
            return jsonify({
                "connected": False,
                "error": str(e)
            })
    
    return app


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="체스 데이터셋 수집 웹 서버")
    parser.add_argument("--port", type=int, default=5004, help="웹 서버 포트 (기본값: 5004)")
    parser.add_argument("--images-dir", type=str, default="images", help="이미지 저장 디렉토리")
    parser.add_argument("--labels-dir", type=str, default="labels", help="라벨 저장 디렉토리")
    parser.add_argument("--camera-index", type=int, default=None, help="카메라 인덱스 (기본값: 자동)")
    parser.add_argument("--model-path", type=str, default="models/chess_piece_model.pt", help="ML 모델 경로 (.pt 파일, 기본값: models/chess_piece_model.pt)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("체스 데이터셋 수집 웹 서버 시작")
    print("=" * 60)
    
    # 카메라 초기화
    try:
        cap = USBCapture(
            index=args.camera_index,
            rotate_180=True,
            rotate_90_cw=False,
            rotate_90_ccw=False
        )
        cap_wrapper = ThreadSafeCapture(cap)
        print(f"[✓] 카메라 초기화 완료: /dev/video{cap.index}")
        
        # 카메라 연결 테스트
        print("[INFO] 카메라 연결 테스트 중...")
        ret, test_frame = cap_wrapper.read()
        if ret and test_frame is not None:
            h, w = test_frame.shape[:2]
            print(f"[✓] 카메라 테스트 성공: {w}x{h} 해상도")
        else:
            print("[WARNING] 카메라 테스트 실패: 프레임을 읽을 수 없습니다")
    except Exception as e:
        print(f"[ERROR] 카메라 초기화 실패: {e}")
        print("[INFO] 사용 가능한 카메라 확인: ls /dev/video*")
        return 1
    
    # 데이터셋 수집기 초기화
    collector = DatasetCollector(
        images_dir=args.images_dir,
        labels_dir=args.labels_dir
    )
    print(f"[✓] 데이터셋 수집기 초기화 완료")
    print(f"    이미지 디렉토리: {collector.images_dir}")
    print(f"    라벨 디렉토리: {collector.labels_dir}")
    print(f"    다음 프레임 번호: {collector.get_next_frame_idx()}")
    
    # ML 모델 초기화 (선택적)
    ml_detector = None
    if args.model_path:
        if not ML_AVAILABLE:
            print("[WARNING] ML 모델을 사용할 수 없습니다. PyTorch가 설치되어 있는지 확인하세요.")
        else:
            model_path = Path(args.model_path)
            if not model_path.is_absolute():
                # 상대 경로인 경우 aicv 디렉토리 기준으로 변환
                model_path = Path(__file__).parent / model_path
            else:
                model_path = Path(args.model_path)
            
            if model_path.exists():
                try:
                    print(f"[ML] 모델 파일 경로: {model_path}")
                    print(f"[ML] 모델 파일 크기: {model_path.stat().st_size / (1024*1024):.2f} MB")
                    ml_detector = ChessPieceMLDetector(str(model_path))
                    print(f"[✓] ML 모델 로드 완료: {model_path}")
                    print(f"[ML] 모델 디바이스: {ml_detector.device}")
                except Exception as e:
                    import traceback
                    print(f"[ML ERROR] ML 모델 로드 실패: {e}")
                    print(f"[ML ERROR] 상세 에러:\n{traceback.format_exc()}")
                    ml_detector = None
            else:
                print(f"[ML WARNING] ML 모델 파일을 찾을 수 없습니다: {model_path}")
                print(f"[ML INFO] 자동 라벨 예측 기능이 비활성화됩니다.")
    else:
        print("[INFO] ML 모델 경로가 제공되지 않았습니다. 자동 라벨 예측 기능이 비활성화됩니다.")
    
    # 웹 앱 생성 및 실행
    app = build_dataset_collector_app(cap_wrapper, collector, ml_detector=ml_detector, port=args.port)
    
    # Flask 기본 로깅 비활성화 (GET/POST 로그 제거)
    import logging
    
    # werkzeug 로거 완전히 비활성화
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.CRITICAL)
    log.disabled = True
    
    # Flask 앱 로거도 비활성화
    app_logger = logging.getLogger('flask')
    app_logger.setLevel(logging.CRITICAL)
    app_logger.disabled = True
    
    print(f"\n[INFO] 웹 서버 시작: http://0.0.0.0:{args.port}")
    print("[INFO] 브라우저에서 위 주소로 접속하세요.")
    print("[INFO] 종료하려면 Ctrl+C를 누르세요.\n")
    
    try:
        app.run(host="0.0.0.0", port=args.port, debug=False, threaded=True)
    except KeyboardInterrupt:
        print("\n[INFO] 서버 종료 중...")
    finally:
        cap_wrapper.release()
        print("[✓] 카메라 해제 완료")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
