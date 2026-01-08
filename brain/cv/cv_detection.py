from __future__ import annotations

import pickle
from typing import Any, Optional

import chess
import numpy as np

from game import game_state
from cv.cv_manager import (
    coord_to_chess_notation,
    process_turn_transition,
    save_initial_board_from_capture,
)

try:
    from aicv.ml_piece_detector import ChessPieceMLDetector
    ML_DETECTOR_AVAILABLE = True
except ImportError:
    ML_DETECTOR_AVAILABLE = False
    ChessPieceMLDetector = None


def default_chess_pieces() -> list[list[str]]:
    return [
        ["BR", "BN", "BB", "BQ", "BK", "BB", "BN", "BR"],
        ["BP", "BP", "BP", "BP", "BP", "BP", "BP", "BP"],
        ["", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", ""],
        ["WP", "WP", "WP", "WP", "WP", "WP", "WP", "WP"],
        ["WR", "WN", "WB", "WQ", "WK", "WB", "WN", "WR"],
    ]


def load_chess_pieces() -> list[list[str]]:
    path = game_state.CHESS_PIECES_PATH
    if path.exists():
        try:
            with open(path, "rb") as file:
                pieces = pickle.load(file)
            if isinstance(pieces, list) and len(pieces) == 8:
                return pieces
        except Exception as exc:
            print(f"[DEBUG] 체스 기물 배열 로드 실패: {exc}")
    return default_chess_pieces()


def detect_move_via_cv() -> Optional[chess.Move]:
    """CV로 기물 변화를 감지하여 체스 이동을 반환."""
    if game_state.cv_capture_wrapper is None:
        print("[CV] 캡처 장치가 초기화되지 않았습니다.")
        return None

    if game_state.chess_pieces_state is None:
        game_state.chess_pieces_state = load_chess_pieces()

    try:
        result = process_turn_transition(
            game_state.cv_capture_wrapper,
            str(game_state.BOARD_VALUES_PATH),
            str(game_state.CHESS_PIECES_PATH),
            game_state.chess_pieces_state,
            game_state.cv_turn_color,
        )
    except Exception as exc:
        print(f"[CV] 턴 전환 처리 실패: {exc}")
        return None

    game_state.cv_turn_color = result["turn_color"]
    game_state.init_board_values = result["init_board_values"]
    game_state.chess_pieces_state = result["chess_pieces"]

    src = result.get("src")
    dst = result.get("dst")
    move_str = result.get("move_str")
    if move_str:
        print(f"[CV] 감지된 이동: {move_str}")

    if src is None or dst is None:
        return None

    move = _resolve_move_from_coords(tuple(src), tuple(dst))
    if move is None:
        print(f"[CV] 합법적인 이동을 찾지 못했습니다: src={src}, dst={dst}")
    return move


def initialize_board_reference() -> Optional[Any]:
    """초기 캡처에서 체스판 기준값을 저장."""
    if game_state.cv_capture_wrapper is None:
        print("[!] 캡처 장치가 없어 체스판 기준값을 초기화할 수 없습니다")
        return None

    board_vals, _ = save_initial_board_from_capture(
        game_state.cv_capture_wrapper, str(game_state.BOARD_VALUES_PATH)
    )
    if board_vals is not None:
        game_state.init_board_values = board_vals
        print("[✓] 체스판 기준값 초기화 완료")
    else:
        print("[!] 체스판 기준값 초기화 실패 - CV 감지 정확도가 낮을 수 있습니다")
    return game_state.init_board_values


def detect_move_via_ml_capture() -> Optional[chess.Move]:
    """
    ML 모델을 사용하여 캡처에서 직접 기물 변화를 감지합니다.
    와핑된 체스판 이미지를 ML 모델에 전달합니다.
    
    Returns:
        chess.Move 또는 None
    """
    print("[ML] detect_move_via_ml_capture() 시작")
    
    if game_state.ml_detector is None:
        print("[ML] ❌ ML detector가 초기화되지 않았습니다.")
        return None
    
    if game_state.cv_capture_wrapper is None:
        print("[ML] ❌ 캡처 장치가 초기화되지 않았습니다.")
        return None
    
    try:
        print("[ML] 프레임 읽기 시도 중...")
        # 프레임 읽기
        ret, frame = game_state.cv_capture_wrapper.read()
        if not ret or frame is None:
            print("[ML] ❌ 프레임을 읽을 수 없습니다.")
            return None
        
        print(f"[ML] ✓ 프레임 읽기 성공: {frame.shape}")
        
        # 와핑된 이미지 얻기
        print("[ML] 와핑 시도 중...")
        from cv.cv_manager import warp_with_manual_corners
        warped_frame = warp_with_manual_corners(frame, size=400)
        
        if warped_frame is None:
            print("[ML] ❌ 와핑 실패")
            return None
        
        print(f"[ML] ✓ 와핑 성공: {warped_frame.shape}")
        
        # 와핑된 이미지를 ML 모델에 전달하여 예측
        print("[ML] ML 모델 예측 시작...")
        current_grid = game_state.ml_detector.predict_frame(warped_frame)
        
        if current_grid is None:
            print("[ML] ❌ 예측 실패 (None 반환)")
            return None
        
        print(f"[ML] ✓ ML 예측 완료: {current_grid.shape}")
        
        # ML 예측 결과 출력 (디버깅용)
        game_state.ml_detector.print_grid(current_grid, "ML 현재 상태 예측")
        
        # 변화 감지
        print("[ML] 변화 감지 시작...")
        move = detect_move_via_ml(current_grid)
        
        if move is None:
            # None이 반환되는 경우는 두 가지:
            # 1. 첫 번째 호출 (기준 상태 저장)
            # 2. 변화 감지 실패 또는 합법적인 이동을 찾지 못함
            if game_state.ml_previous_grid is not None:
                # 기준 상태가 이미 있으면 변화 감지 실패
                print("[ML] ❌ 변화 감지 실패 또는 이동을 찾지 못함")
            else:
                # 기준 상태가 없으면 첫 번째 호출 (정상)
                print("[ML] ✓ 기준 상태 저장 완료 (정상 동작)")
        else:
            print(f"[ML] ✓ 변화 감지 성공: {move.uci()}")
        
        return move
        
    except Exception as exc:
        print(f"[ML] ❌ ML 기반 CV 감지 중 예외 발생: {exc}")
        import traceback
        print("[ML] 상세 에러:")
        traceback.print_exc()
        return None


def board_to_grid(board: chess.Board) -> np.ndarray:
    """
    chess.Board 객체를 8x8 그리드로 변환합니다.
    
    Args:
        board: chess.Board 객체
        
    Returns:
        8x8 numpy 배열 (0=empty, 1=white, 2=black)
        - grid[r, c] = 체스 좌표 (file=a+c, rank=8-r)에 해당
        - 예: grid[0, 0] = a8, grid[7, 7] = h1
    """
    grid = np.zeros((8, 8), dtype=int)
    
    for r in range(8):  # row 0 = rank 8, row 7 = rank 1
        for c in range(8):  # col 0 = file a, col 7 = file h
            rank = 8 - r  # rank 8, 7, 6, ..., 1
            file = c  # file a=0, b=1, ..., h=7
            
            # chess.Board에서 square 번호 계산
            # square = rank * 8 + file (rank는 1-8, 여기서는 0-7로 변환 필요)
            square = (rank - 1) * 8 + file
            
            piece = board.piece_at(square)
            if piece is None:
                grid[r, c] = 0  # 빈칸
            elif piece.color == chess.WHITE:
                grid[r, c] = 1  # 흰색
            else:
                grid[r, c] = 2  # 검은색
    
    return grid


def detect_move_via_ml(current_grid: np.ndarray, previous_grid: Optional[np.ndarray] = None) -> Optional[chess.Move]:
    """
    ML 모델의 8x8 배열을 보드 상태와 비교하여 움직임을 감지합니다.
    
    Args:
        current_grid: ML이 인식한 현재 카메라 상태 8x8 배열 (0=empty, 1=white, 2=black)
        previous_grid: 사용하지 않음 (game_state.current_board에서 가져옴)
        
    Returns:
        chess.Move 또는 None
    """
    # 현재 보드 상태를 8x8 그리드로 변환
    board_grid = board_to_grid(game_state.current_board)
    
    print("[ML] 보드 상태와 카메라 인식 결과 비교 중...")
    print("[ML] 현재 보드 상태 (소프트웨어):")
    if game_state.ml_detector:
        game_state.ml_detector.print_grid(board_grid, "보드 상태")
    
    print("[ML] 카메라 인식 결과 (ML):")
    if game_state.ml_detector:
        game_state.ml_detector.print_grid(current_grid, "카메라 인식")
    
    # 현재 차례의 색깔 확인 (1=흰색, 2=검은색)
    current_turn_color = 1 if game_state.current_board.turn == chess.WHITE else 2
    turn_name = "흰색" if current_turn_color == 1 else "검은색"
    print(f"[ML] 현재 차례: {turn_name} (색상 코드: {current_turn_color})")
    
    # 변화 감지 (보드 상태와 카메라 인식 비교, 현재 차례 색깔의 기물 변화만 고려)
    changes = []
    for r in range(8):
        for c in range(8):
            board_val = board_grid[r, c]  # 보드에 반영된 상태
            camera_val = current_grid[r, c]  # 카메라로 본 실제 상태
            if board_val != camera_val:
                # 현재 차례 색깔과 관련된 변화만 추가
                # 출발지: 보드에는 현재 차례 기물이 있는데 카메라에는 없음
                # 도착지: 보드에는 없는데 카메라에는 현재 차례 기물이 있음
                is_relevant = False
                if board_val == current_turn_color and camera_val != current_turn_color:
                    # 출발지: 보드에 현재 차례 기물이 있는데 카메라에는 없음/다름
                    is_relevant = True
                elif camera_val == current_turn_color and board_val != current_turn_color:
                    # 도착지: 카메라에 현재 차례 기물이 있는데 보드에는 없음/다름
                    is_relevant = True
                
                if is_relevant:
                    changes.append((r, c, board_val, camera_val))
    
    if len(changes) == 0:
        print("[ML] 변화가 감지되지 않았습니다.")
        return None
    
    print(f"[ML] {len(changes)}개 칸에서 변화 감지:")
    for i, (r, c, board_val, camera_val) in enumerate(changes):
        board_str = {0: "빈칸", 1: "흰색", 2: "검은색"}.get(board_val, f"?({board_val})")
        camera_str = {0: "빈칸", 1: "흰색", 2: "검은색"}.get(camera_val, f"?({camera_val})")
        file = chr(ord('a') + c)
        rank = str(8 - r)
        print(f"  [{i+1}] ({r},{c}) = {file}{rank}: 보드={board_str}, 카메라={camera_str}")
    
    # 변화 분석
    if len(changes) == 1:
        # 한 칸만 변화 - 이동을 감지할 수 없음
        r, c, board_val, camera_val = changes[0]
        file = chr(ord('a') + c)
        rank = str(8 - r)
        board_str = {0: "빈칸", 1: "흰색", 2: "검은색"}.get(board_val, f"?({board_val})")
        camera_str = {0: "빈칸", 1: "흰색", 2: "검은색"}.get(camera_val, f"?({camera_val})")
        print(f"[ML] 한 칸만 변화: {file}{rank} (보드: {board_str}, 카메라: {camera_str})")
        print("[ML] 한 칸만 변화 - 출발지와 도착지를 모두 알 수 없음")
        return None
    
    elif len(changes) == 2:
        # 일반적인 이동: 2개 칸 변화
        print("[ML] 2개 칸 변화 - 일반 이동 처리")
        r1, c1, board1, camera1 = changes[0]
        r2, c2, board2, camera2 = changes[1]
        
        # 출발지: 보드에는 기물이 있는데 카메라에는 없음
        # 도착지: 보드에는 없는데 카메라에는 기물이 있음
        src = None
        dst = None
        
        if board1 == current_turn_color and camera1 != current_turn_color:
            # 첫 번째 칸: 보드에 현재 차례 기물 있음, 카메라에는 없음 → 출발지
            src = (r1, c1)
            if camera2 == current_turn_color:
                # 두 번째 칸: 카메라에 현재 차례 기물 있음 → 도착지
                dst = (r2, c2)
            else:
                dst = (r2, c2)
        elif board2 == current_turn_color and camera2 != current_turn_color:
            # 두 번째 칸: 보드에 현재 차례 기물 있음, 카메라에는 없음 → 출발지
            src = (r2, c2)
            if camera1 == current_turn_color:
                # 첫 번째 칸: 카메라에 현재 차례 기물 있음 → 도착지
                dst = (r1, c1)
            else:
                dst = (r1, c1)
        else:
            # 둘 다 다른 패턴 - 두 가지 순서 모두 시도
            src = (r1, c1)
            dst = (r2, c2)
        
        if src is None or dst is None:
            print("[ML] src/dst를 결정할 수 없습니다.")
            return None
        
        src_file = chr(ord('a') + src[1])
        src_rank = str(8 - src[0])
        dst_file = chr(ord('a') + dst[1])
        dst_rank = str(8 - dst[0])
        print(f"[ML] 감지된 이동: src={src_file}{src_rank}, dst={dst_file}{dst_rank}")
        
        # chess.Move로 변환 (두 가지 순서 모두 시도)
        print(f"[ML] 체스 좌표 변환 시도 중...")
        move = _resolve_move_from_coords(src, dst)
        
        if move is not None:
            print(f"[ML] ✅ 이동 변환 성공: {move.uci()} (SAN: {game_state.current_board.san(move)})")
            return move
        else:
            print(f"[ML] ❌ 합법적인 이동을 찾지 못했습니다: src={src_file}{src_rank}, dst={dst_file}{dst_rank}")
            print(f"[ML] 현재 보드 상태:")
            print(f"[ML]   FEN: {game_state.current_board.fen()}")
            print(f"[ML]   합법적인 이동 목록 (처음 10개):")
            legal_moves = list(game_state.current_board.legal_moves)
            for i, legal_move in enumerate(legal_moves[:10]):
                print(f"[ML]     {i+1}. {legal_move.uci()}")
            if len(legal_moves) > 10:
                print(f"[ML]     ... 외 {len(legal_moves) - 10}개")
            return None
    
    else:
        # 3개 이상 변화 - 특수 수 (캐슬링, 앙파상 등) 처리
        # 모든 (src, dst) 조합을 시도하여 합법적인 수 찾기
        print(f"[ML] {len(changes)}개 칸 변화 - 특수 수 가능성 (모든 조합 시도)")
        coords = [(r, c) for (r, c, _, _) in changes]
        
        # 모든 순서쌍 (src, dst) 생성
        candidates = []
        for i in range(len(coords)):
            for j in range(len(coords)):
                if i != j:
                    candidates.append((coords[i], coords[j]))
        
        print(f"[ML] 총 {len(candidates)}개의 (src, dst) 조합을 시도합니다.")
        
        # 각 조합을 시도하여 합법적인 수 찾기
        for idx, (src, dst) in enumerate(candidates):
            src_file = chr(ord('a') + src[1])
            src_rank = str(8 - src[0])
            dst_file = chr(ord('a') + dst[1])
            dst_rank = str(8 - dst[0])
            
            if idx < 5 or idx == len(candidates) - 1:  # 처음 5개와 마지막만 출력
                print(f"[ML]   조합 {idx+1}/{len(candidates)}: {src_file}{src_rank} → {dst_file}{dst_rank}")
            
            # chess.Move로 변환 시도
            move = _resolve_move_from_coords(src, dst)
            
            if move is not None:
                # 합법적인 이동 발견!
                print(f"[ML] ✅ 합법적인 이동 발견 (조합 {idx+1}/{len(candidates)}): {move.uci()} (SAN: {game_state.current_board.san(move)})")
                
                # 특수 수인지 확인하여 로그 출력
                if game_state.current_board.is_castling(move):
                    print(f"[ML]   → 캐슬링 감지됨!")
                elif game_state.current_board.is_en_passant(move):
                    print(f"[ML]   → 앙파상 감지됨!")
                elif move.promotion:
                    print(f"[ML]   → 프로모션 감지됨!")
                
                return move
        
        # 모든 조합을 시도했지만 합법적인 이동을 찾지 못함
        print(f"[ML] ❌ 모든 {len(candidates)}개 조합을 시도했지만 합법적인 이동을 찾지 못했습니다.")
        print(f"[ML] 현재 보드 상태:")
        print(f"[ML]   FEN: {game_state.current_board.fen()}")
        print(f"[ML]   합법적인 이동 목록 (처음 10개):")
        legal_moves = list(game_state.current_board.legal_moves)
        for i, legal_move in enumerate(legal_moves[:10]):
            print(f"[ML]     {i+1}. {legal_move.uci()}")
        if len(legal_moves) > 10:
            print(f"[ML]     ... 외 {len(legal_moves) - 10}개")
        
        return None


def _resolve_move_from_coords(
    src: tuple[int, int], dst: tuple[int, int]
) -> Optional[chess.Move]:
    """격자 좌표(src/dst)를 체스 Move로 변환."""
    candidates = [(src, dst)]
    if src != dst:
        candidates.append((dst, src))

    print(f"[ML] 좌표 변환 후보: {len(candidates)}개")
    
    for idx, (from_coord, to_coord) in enumerate(candidates):
        from_name = coord_to_chess_notation(from_coord[0], from_coord[1])
        to_name = coord_to_chess_notation(to_coord[0], to_coord[1])
        print(f"[ML]   후보 {idx+1}: {from_name} → {to_name}")
        
        try:
            from_sq = chess.parse_square(from_name)
            to_sq = chess.parse_square(to_name)
            print(f"[ML]     정사각형 번호: {from_sq} → {to_sq}")
        except ValueError as e:
            print(f"[ML]     ❌ 정사각형 파싱 실패: {e}")
            continue

        # 출발지에 기물이 있는지 확인
        piece = game_state.current_board.piece_at(from_sq)
        if piece is None:
            print(f"[ML]     ⚠️ 출발지 {from_name}에 기물이 없습니다.")
        else:
            piece_name = {chess.PAWN: "폰", chess.ROOK: "룩", chess.KNIGHT: "나이트", 
                         chess.BISHOP: "비숍", chess.QUEEN: "퀸", chess.KING: "킹"}.get(piece.piece_type, "?")
            color_name = "흰색" if piece.color == chess.WHITE else "검은색"
            print(f"[ML]     출발지 기물: {color_name} {piece_name}")

        promotions: list[Optional[chess.PieceType]] = [None]
        if piece and piece.piece_type == chess.PAWN and to_name[1] in ("1", "8"):
            promotions = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
            print(f"[ML]     폰 프로모션 가능: {to_name[1]}랭크")

        for promo in promotions:
            move = chess.Move(from_sq, to_sq, promotion=promo)
            promo_str = f" (프로모션: {promo})" if promo else ""
            if move in game_state.current_board.legal_moves:
                print(f"[ML]     ✅ 합법적인 이동 발견: {move.uci()}{promo_str}")
                return move
            else:
                print(f"[ML]     ❌ 합법적이지 않은 이동: {move.uci()}{promo_str}")
    
    print(f"[ML]   모든 후보를 시도했지만 합법적인 이동을 찾지 못했습니다.")
    return None

