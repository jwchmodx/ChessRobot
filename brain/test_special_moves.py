#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
캐슬링과 앙파상 인식 테스트 스크립트

1. 시뮬레이션 모드: 카메라 없이 빠르게 테스트
2. 물리적 체스판 모드: 실제 체스판에서 사용자가 수를 두고 인식 확인
"""

from __future__ import annotations

import sys
from pathlib import Path

# 프로젝트 루트를 경로에 추가
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import os
import chess
import numpy as np
from game import game_state
from game.board_display import _print_board
from cv.cv_detection import board_to_grid, detect_move_via_ml, detect_move_via_ml_capture
from cv.cv_web import USBCapture, ThreadSafeCapture


def print_grid(grid, title="그리드"):
    """8x8 그리드를 출력"""
    print(f"\n{title}:")
    print("  " + " ".join(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']))
    for r in range(8):
        rank = 8 - r
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


def test_castling_kingside_white():
    """흰색 킹사이드 캐슬링 테스트"""
    print("=" * 60)
    print("테스트 1: 흰색 킹사이드 캐슬링 (e1 → g1, h1 → f1)")
    print("=" * 60)
    
    # 캐슬링 가능한 포지션 설정
    # 킹과 룩이 움직이지 않았고, 사이에 기물이 없는 상태
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQK2R w KQkq - 0 1"
    
    # 초기 보드 상태 설정 (이전 상태 - CV 인식 전)
    game_state.current_board = chess.Board(fen)
    
    print(f"초기 FEN: {fen}")
    print(f"현재 차례: {'흰색' if game_state.current_board.turn == chess.WHITE else '검은색'}")
    print(f"캐슬링 가능: {game_state.current_board.has_kingside_castling_rights(chess.WHITE)}")
    
    # 초기 보드 상태 (이전 상태 - game_state.current_board)
    initial_grid = board_to_grid(game_state.current_board)
    print_grid(initial_grid, "이전 보드 상태 (game_state.current_board - CV 인식 전)")
    
    # 캐슬링 실행 (e1→g1, h1→f1)
    castling_move = chess.Move.from_uci("e1g1")
    if castling_move in game_state.current_board.legal_moves:
        print(f"✅ 합법적인 캐슬링 수: {castling_move.uci()}")
        
        # 수를 실행해서 보드 상태 변경
        game_state.current_board.push(castling_move)
        
        # 캐슬링 후 보드 상태 (카메라가 인식한 상태 - current_grid)
        after_grid = board_to_grid(game_state.current_board)
        print_grid(after_grid, "현재 보드 상태 (카메라 인식 결과 - current_grid)")
        
        # 보드를 원래 상태로 되돌림 (CV 인식 시뮬레이션을 위해)
        # 이제 game_state.current_board는 "이전 상태"가 됨
        game_state.current_board.pop()
        
        print("\n[CV 인식 시뮬레이션]")
        print("game_state.current_board: 이전 상태 (캐슬링 전)")
        print("after_grid: 현재 상태 (캐슬링 후 - 카메라 인식)")
        print("→ detect_move_via_ml()이 이 둘을 비교하여 변화를 감지합니다\n")
        
        # CV 인식 시뮬레이션: detect_move_via_ml 호출
        detected_move = detect_move_via_ml(after_grid)
        
        if detected_move:
            print(f"\n✅ 인식 성공: {detected_move.uci()}")
            print(f"   SAN: {game_state.current_board.san(detected_move)}")
            
            # 캐슬링인지 확인
            if game_state.current_board.is_castling(detected_move):
                print("   ✅ 캐슬링으로 올바르게 인식됨!")
                return True
            else:
                print("   ❌ 캐슬링으로 인식되지 않음")
                return False
        else:
            print("\n❌ 인식 실패: None 반환")
            return False
    else:
        print(f"❌ {castling_move.uci()}는 현재 포지션에서 합법적이지 않습니다")
        return False


def test_castling_queenside_black():
    """검은색 퀸사이드 캐슬링 테스트"""
    print("\n" + "=" * 60)
    print("테스트 2: 검은색 퀸사이드 캐슬링 (e8 → c8, a8 → d8)")
    print("=" * 60)
    
    # 검은색 퀸사이드 캐슬링 가능한 포지션
    fen = "r3kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"
    
    # 초기 보드 상태 설정 (이전 상태)
    game_state.current_board = chess.Board(fen)
    
    print(f"초기 FEN: {fen}")
    print(f"현재 차례: {'흰색' if game_state.current_board.turn == chess.WHITE else '검은색'}")
    print(f"캐슬링 가능: {game_state.current_board.has_queenside_castling_rights(chess.BLACK)}")
    
    # 초기 보드 상태 (이전 상태)
    initial_grid = board_to_grid(game_state.current_board)
    print_grid(initial_grid, "이전 보드 상태 (game_state.current_board - CV 인식 전)")
    
    # 캐슬링 실행 (e8→c8, a8→d8)
    castling_move = chess.Move.from_uci("e8c8")
    if castling_move in game_state.current_board.legal_moves:
        print(f"✅ 합법적인 캐슬링 수: {castling_move.uci()}")
        game_state.current_board.push(castling_move)
        
        # 캐슬링 후 보드 상태 (카메라 인식 결과)
        after_grid = board_to_grid(game_state.current_board)
        print_grid(after_grid, "현재 보드 상태 (카메라 인식 결과 - current_grid)")
        
        # 보드를 원래 상태로 되돌림
        game_state.current_board.pop()
        
        print("\n[CV 인식 시뮬레이션]")
        print("game_state.current_board: 이전 상태 (캐슬링 전)")
        print("after_grid: 현재 상태 (캐슬링 후 - 카메라 인식)")
        print("→ detect_move_via_ml()이 이 둘을 비교하여 변화를 감지합니다\n")
        
        # CV 인식 시뮬레이션
        detected_move = detect_move_via_ml(after_grid)
        
        if detected_move:
            print(f"\n✅ 인식 성공: {detected_move.uci()}")
            print(f"   SAN: {game_state.current_board.san(detected_move)}")
            
            if game_state.current_board.is_castling(detected_move):
                print("   ✅ 캐슬링으로 올바르게 인식됨!")
                return True
            else:
                print("   ❌ 캐슬링으로 인식되지 않음")
                return False
        else:
            print("\n❌ 인식 실패: None 반환")
            return False
    else:
        print(f"❌ {castling_move.uci()}는 현재 포지션에서 합법적이지 않습니다")
        return False


def test_en_passant_white():
    """흰색 앙파상 테스트"""
    print("\n" + "=" * 60)
    print("테스트 3: 흰색 앙파상 (e5 → d6, d5의 폰 제거)")
    print("=" * 60)
    
    # 앙파상 가능한 포지션 설정
    # 검은색이 d7→d5로 이동한 직후, 흰색이 e5에서 앙파상 가능
    fen = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
    
    # 초기 보드 상태 설정 (이전 상태)
    game_state.current_board = chess.Board(fen)
    
    print(f"초기 FEN: {fen}")
    print(f"현재 차례: {'흰색' if game_state.current_board.turn == chess.WHITE else '검은색'}")
    print(f"앙파상 가능: d6")
    
    # 초기 보드 상태 (이전 상태)
    initial_grid = board_to_grid(game_state.current_board)
    print_grid(initial_grid, "이전 보드 상태 (game_state.current_board - CV 인식 전)")
    print("설명: e5에 흰색 폰, d5에 검은색 폰이 있음")
    print("      흰색이 e5→d6로 앙파상하면 d5의 검은색 폰이 제거됨")
    
    # 앙파상 실행 (e5→d6)
    en_passant_move = chess.Move.from_uci("e5d6")
    if en_passant_move in game_state.current_board.legal_moves:
        print(f"✅ 합법적인 앙파상 수: {en_passant_move.uci()}")
        game_state.current_board.push(en_passant_move)
        
        # 앙파상 후 보드 상태 (카메라 인식 결과)
        after_grid = board_to_grid(game_state.current_board)
        print_grid(after_grid, "현재 보드 상태 (카메라 인식 결과 - current_grid)")
        print("설명: e5가 비어있고, d6에 흰색 폰, d5도 비어있음 (검은색 폰 제거됨)")
        
        # 보드를 원래 상태로 되돌림
        game_state.current_board.pop()
        
        print("\n[CV 인식 시뮬레이션]")
        print("game_state.current_board: 이전 상태 (앙파상 전)")
        print("after_grid: 현재 상태 (앙파상 후 - 카메라 인식)")
        print("→ detect_move_via_ml()이 이 둘을 비교하여 변화를 감지합니다\n")
        
        # CV 인식 시뮬레이션
        detected_move = detect_move_via_ml(after_grid)
        
        if detected_move:
            print(f"\n✅ 인식 성공: {detected_move.uci()}")
            print(f"   SAN: {game_state.current_board.san(detected_move)}")
            
            if game_state.current_board.is_en_passant(detected_move):
                print("   ✅ 앙파상으로 올바르게 인식됨!")
                return True
            else:
                print("   ❌ 앙파상으로 인식되지 않음")
                print(f"   인식된 수 타입: 일반 이동")
                return False
        else:
            print("\n❌ 인식 실패: None 반환")
            return False
    else:
        print(f"❌ {en_passant_move.uci()}는 현재 포지션에서 합법적이지 않습니다")
        print("   합법적인 수 목록:")
        for move in list(game_state.current_board.legal_moves)[:10]:
            print(f"     - {move.uci()}")
        return False


def test_en_passant_black():
    """검은색 앙파상 테스트"""
    print("\n" + "=" * 60)
    print("테스트 4: 검은색 앙파상 (d4 → e3, e4의 폰 제거)")
    print("=" * 60)
    
    # 검은색 앙파상 가능한 포지션
    # 흰색이 e2→e4로 이동한 직후, 검은색이 d4에서 앙파상 가능
    fen = "rnbqkbnr/pppppppp/8/8/3Pp3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 2"
    
    # 초기 보드 상태 설정 (이전 상태)
    game_state.current_board = chess.Board(fen)
    
    print(f"초기 FEN: {fen}")
    print(f"현재 차례: {'흰색' if game_state.current_board.turn == chess.WHITE else '검은색'}")
    print(f"앙파상 가능: e3")
    
    # 초기 보드 상태 (이전 상태)
    initial_grid = board_to_grid(game_state.current_board)
    print_grid(initial_grid, "이전 보드 상태 (game_state.current_board - CV 인식 전)")
    print("설명: d4에 검은색 폰, e4에 흰색 폰이 있음")
    print("      검은색이 d4→e3로 앙파상하면 e4의 흰색 폰이 제거됨")
    
    # 앙파상 실행 (d4→e3)
    en_passant_move = chess.Move.from_uci("d4e3")
    if en_passant_move in game_state.current_board.legal_moves:
        print(f"✅ 합법적인 앙파상 수: {en_passant_move.uci()}")
        game_state.current_board.push(en_passant_move)
        
        # 앙파상 후 보드 상태 (카메라 인식 결과)
        after_grid = board_to_grid(game_state.current_board)
        print_grid(after_grid, "현재 보드 상태 (카메라 인식 결과 - current_grid)")
        
        # 보드를 원래 상태로 되돌림
        game_state.current_board.pop()
        
        print("\n[CV 인식 시뮬레이션]")
        print("game_state.current_board: 이전 상태 (앙파상 전)")
        print("after_grid: 현재 상태 (앙파상 후 - 카메라 인식)")
        print("→ detect_move_via_ml()이 이 둘을 비교하여 변화를 감지합니다\n")
        
        # CV 인식 시뮬레이션
        detected_move = detect_move_via_ml(after_grid)
        
        if detected_move:
            print(f"\n✅ 인식 성공: {detected_move.uci()}")
            print(f"   SAN: {game_state.current_board.san(detected_move)}")
            
            if game_state.current_board.is_en_passant(detected_move):
                print("   ✅ 앙파상으로 올바르게 인식됨!")
                return True
            else:
                print("   ❌ 앙파상으로 인식되지 않음")
                return False
        else:
            print("\n❌ 인식 실패: None 반환")
            return False
    else:
        print(f"❌ {en_passant_move.uci()}는 현재 포지션에서 합법적이지 않습니다")
        return False


def test_castling_kingside_white_physical():
    """실제 체스판에서 흰색 킹사이드 캐슬링 테스트"""
    print("=" * 60)
    print("물리적 체스판 테스트: 흰색 킹사이드 캐슬링")
    print("=" * 60)
    
    # 캐슬링 가능한 포지션 설정
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQK2R w KQkq - 0 1"
    game_state.current_board = chess.Board(fen)
    
    print(f"\n초기 FEN: {fen}")
    print(f"현재 차례: {'흰색' if game_state.current_board.turn == chess.WHITE else '검은색'}")
    print(f"캐슬링 가능: {game_state.current_board.has_kingside_castling_rights(chess.WHITE)}")
    
    # 목표 보드 상태 출력
    initial_grid = board_to_grid(game_state.current_board)
    print_grid(initial_grid, "목표 보드 상태 (체스판을 이렇게 배치하세요)")
    
    print("\n" + "=" * 60)
    print("📋 준비 사항:")
    print("1. 체스판을 위 상태로 배치하세요")
    print("2. 흰색 킹(e1)과 룩(h1)이 초기 위치에 있어야 합니다")
    print("3. 킹-룩 사이(f1, g1)가 비어있어야 합니다")
    print("=" * 60)
    
    input("\n체스판을 준비하셨으면 엔터를 누르세요...")
    
    # 초기 상태를 기준으로 저장 (첫 호출)
    print("\n[1단계] 초기 상태를 기준으로 저장 중...")
    # ml_previous_grid가 None인지 확인하여 첫 호출인지 판단
    was_first_call = (game_state.ml_previous_grid is None)
    first_result = detect_move_via_ml_capture()
    
    # 첫 호출이었고 이제 ml_previous_grid가 설정되었으면 성공
    if was_first_call and game_state.ml_previous_grid is not None:
        print("✅ 초기 상태 저장 완료")
    elif first_result is None:
        print("✅ 초기 상태 저장 완료 (변화 없음)")
    else:
        print("⚠️  초기 상태에서 변화가 감지되었습니다.")
        print(f"   감지된 수: {first_result.uci() if first_result else None}")
        print("   체스판이 목표 상태와 일치하는지 확인하세요.")
        # 그래도 계속 진행 (사용자가 이미 캐슬링을 했을 수도 있음)
        print("   계속 진행합니다...")
    
    print("\n" + "=" * 60)
    print("🎯 이제 캐슬링을 수행하세요!")
    print("   - 흰색 킹(e1)을 g1로 이동")
    print("   - 흰색 룩(h1)을 f1로 이동")
    print("=" * 60)
    
    input("\n캐슬링을 완료하셨으면 엔터를 누르세요...")
    
    # 이전 보드 상태 저장 (인식 전)
    board_before = game_state.current_board.copy()
    
    # 이전 보드 상태 출력
    print("\n" + "=" * 60)
    print("이전 보드 상태 (캐슬링 전)")
    print("=" * 60)
    _print_board(board_before)
    
    # 캐슬링 후 상태 인식
    print("\n[2단계] 캐슬링 후 상태를 인식 중...")
    detected_move = detect_move_via_ml_capture()
    
    if detected_move:
        print(f"\n✅ 인식 성공: {detected_move.uci()}")
        print(f"   SAN: {game_state.current_board.san(detected_move)}")
        
        # 이동 적용
        game_state.current_board.push(detected_move)
        
        # 이동 적용 후 보드 상태 출력
        print("\n" + "=" * 60)
        print("이후 보드 상태 (캐슬링 후 - 이동 적용)")
        print("=" * 60)
        _print_board(game_state.current_board)
        print("=" * 60)
        
        # 보드 되돌리기 (테스트용)
        game_state.current_board.pop()
        
        if board_before.is_castling(detected_move):
            print("\n   ✅ 캐슬링으로 올바르게 인식됨!")
            return True
        else:
            print("\n   ❌ 캐슬링으로 인식되지 않음")
            print(f"   인식된 수 타입: 일반 이동")
            return False
    else:
        print("\n❌ 인식 실패: None 반환")
        print("   체스판 상태를 확인하고 다시 시도하세요.")
        # 실패해도 보드 상태는 출력
        print("\n" + "=" * 60)
        print("현재 보드 상태 (인식 실패)")
        print("=" * 60)
        _print_board(board_before)
        print("=" * 60)
        return False


def test_castling_queenside_black_physical():
    """실제 체스판에서 검은색 퀸사이드 캐슬링 테스트"""
    print("=" * 60)
    print("물리적 체스판 테스트: 검은색 퀸사이드 캐슬링")
    print("=" * 60)
    
    fen = "r3kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1"
    game_state.current_board = chess.Board(fen)
    
    print(f"\n초기 FEN: {fen}")
    print(f"현재 차례: {'흰색' if game_state.current_board.turn == chess.WHITE else '검은색'}")
    print(f"캐슬링 가능: {game_state.current_board.has_queenside_castling_rights(chess.BLACK)}")
    
    initial_grid = board_to_grid(game_state.current_board)
    print_grid(initial_grid, "목표 보드 상태 (체스판을 이렇게 배치하세요)")
    
    print("\n📋 준비 사항:")
    print("1. 검은색 킹(e8)과 룩(a8)이 초기 위치에 있어야 합니다")
    print("2. 킹-룩 사이(b8, c8, d8)가 비어있어야 합니다")
    
    input("\n체스판을 준비하셨으면 엔터를 누르세요...")
    
    print("\n[1단계] 초기 상태를 기준으로 저장 중...")
    was_first_call = (game_state.ml_previous_grid is None)
    first_result = detect_move_via_ml_capture()
    
    if was_first_call and game_state.ml_previous_grid is not None:
        print("✅ 초기 상태 저장 완료")
    elif first_result is None:
        print("✅ 초기 상태 저장 완료 (변화 없음)")
    else:
        print("⚠️  초기 상태에서 변화가 감지되었습니다.")
        print("   계속 진행합니다...")
    
    print("\n🎯 이제 캐슬링을 수행하세요!")
    print("   - 검은색 킹(e8)을 c8로 이동")
    print("   - 검은색 룩(a8)을 d8로 이동")
    
    input("\n캐슬링을 완료하셨으면 엔터를 누르세요...")
    
    # 이전 보드 상태 저장
    board_before = game_state.current_board.copy()
    
    # 이전 보드 상태 출력
    print("\n" + "=" * 60)
    print("이전 보드 상태 (캐슬링 전)")
    print("=" * 60)
    _print_board(board_before)
    
    print("\n[2단계] 캐슬링 후 상태를 인식 중...")
    detected_move = detect_move_via_ml_capture()
    
    if detected_move:
        print(f"\n✅ 인식 성공: {detected_move.uci()}")
        print(f"   SAN: {game_state.current_board.san(detected_move)}")
        
        # 이동 적용
        game_state.current_board.push(detected_move)
        
        # 이동 적용 후 보드 상태 출력
        print("\n" + "=" * 60)
        print("이후 보드 상태 (캐슬링 후 - 이동 적용)")
        print("=" * 60)
        _print_board(game_state.current_board)
        print("=" * 60)
        
        # 보드 되돌리기 (테스트용)
        game_state.current_board.pop()
        
        if board_before.is_castling(detected_move):
            print("\n   ✅ 캐슬링으로 올바르게 인식됨!")
            return True
        else:
            print("\n   ❌ 캐슬링으로 인식되지 않음")
            return False
    else:
        print("\n❌ 인식 실패")
        # 실패해도 보드 상태는 출력
        print("\n" + "=" * 60)
        print("현재 보드 상태 (인식 실패)")
        print("=" * 60)
        _print_board(board_before)
        print("=" * 60)
        return False


def test_en_passant_white_physical():
    """실제 체스판에서 흰색 앙파상 테스트"""
    print("=" * 60)
    print("물리적 체스판 테스트: 흰색 앙파상")
    print("=" * 60)
    
    fen = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
    game_state.current_board = chess.Board(fen)
    
    print(f"\n초기 FEN: {fen}")
    print(f"현재 차례: {'흰색' if game_state.current_board.turn == chess.WHITE else '검은색'}")
    
    initial_grid = board_to_grid(game_state.current_board)
    print_grid(initial_grid, "목표 보드 상태 (체스판을 이렇게 배치하세요)")
    
    print("\n설명:")
    print("- e5에 흰색 폰")
    print("- d5에 검은색 폰")
    print("- 흰색이 e5→d6로 앙파상하면 d5의 검은색 폰이 제거됨")
    
    input("\n체스판을 준비하셨으면 엔터를 누르세요...")
    
    print("\n[1단계] 초기 상태를 기준으로 저장 중...")
    was_first_call = (game_state.ml_previous_grid is None)
    first_result = detect_move_via_ml_capture()
    
    if was_first_call and game_state.ml_previous_grid is not None:
        print("✅ 초기 상태 저장 완료")
    elif first_result is None:
        print("✅ 초기 상태 저장 완료 (변화 없음)")
    else:
        print("⚠️  초기 상태에서 변화가 감지되었습니다.")
        print("   계속 진행합니다...")
    
    print("\n🎯 이제 앙파상을 수행하세요!")
    print("   - e5의 흰색 폰을 d6로 이동")
    print("   - d5의 검은색 폰이 자동으로 제거됨")
    
    input("\n앙파상을 완료하셨으면 엔터를 누르세요...")
    
    # 이전 보드 상태 저장
    board_before = game_state.current_board.copy()
    
    # 이전 보드 상태 출력
    print("\n" + "=" * 60)
    print("이전 보드 상태 (앙파상 전)")
    print("=" * 60)
    _print_board(board_before)
    
    print("\n[2단계] 앙파상 후 상태를 인식 중...")
    detected_move = detect_move_via_ml_capture()
    
    if detected_move:
        print(f"\n✅ 인식 성공: {detected_move.uci()}")
        print(f"   SAN: {game_state.current_board.san(detected_move)}")
        
        # 이동 적용
        game_state.current_board.push(detected_move)
        
        # 이동 적용 후 보드 상태 출력
        print("\n" + "=" * 60)
        print("이후 보드 상태 (앙파상 후 - 이동 적용)")
        print("=" * 60)
        _print_board(game_state.current_board)
        print("=" * 60)
        
        # 보드 되돌리기 (테스트용)
        game_state.current_board.pop()
        
        if board_before.is_en_passant(detected_move):
            print("\n   ✅ 앙파상으로 올바르게 인식됨!")
            return True
        else:
            print("\n   ❌ 앙파상으로 인식되지 않음")
            return False
    else:
        print("\n❌ 인식 실패")
        # 실패해도 보드 상태는 출력
        print("\n" + "=" * 60)
        print("현재 보드 상태 (인식 실패)")
        print("=" * 60)
        _print_board(board_before)
        print("=" * 60)
        return False


def test_en_passant_black_physical():
    """실제 체스판에서 검은색 앙파상 테스트"""
    print("=" * 60)
    print("물리적 체스판 테스트: 검은색 앙파상")
    print("=" * 60)
    
    fen = "rnbqkbnr/pppppppp/8/8/3Pp3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 2"
    game_state.current_board = chess.Board(fen)
    
    print(f"\n초기 FEN: {fen}")
    print(f"현재 차례: {'흰색' if game_state.current_board.turn == chess.WHITE else '검은색'}")
    
    initial_grid = board_to_grid(game_state.current_board)
    print_grid(initial_grid, "목표 보드 상태 (체스판을 이렇게 배치하세요)")
    
    print("\n설명:")
    print("- d4에 검은색 폰")
    print("- e4에 흰색 폰")
    print("- 검은색이 d4→e3로 앙파상하면 e4의 흰색 폰이 제거됨")
    
    input("\n체스판을 준비하셨으면 엔터를 누르세요...")
    
    print("\n[1단계] 초기 상태를 기준으로 저장 중...")
    was_first_call = (game_state.ml_previous_grid is None)
    first_result = detect_move_via_ml_capture()
    
    if was_first_call and game_state.ml_previous_grid is not None:
        print("✅ 초기 상태 저장 완료")
    elif first_result is None:
        print("✅ 초기 상태 저장 완료 (변화 없음)")
    else:
        print("⚠️  초기 상태에서 변화가 감지되었습니다.")
        print("   계속 진행합니다...")
    
    print("\n🎯 이제 앙파상을 수행하세요!")
    print("   - d4의 검은색 폰을 e3로 이동")
    print("   - e4의 흰색 폰이 자동으로 제거됨")
    
    input("\n앙파상을 완료하셨으면 엔터를 누르세요...")
    
    # 이전 보드 상태 저장
    board_before = game_state.current_board.copy()
    
    # 이전 보드 상태 출력
    print("\n" + "=" * 60)
    print("이전 보드 상태 (앙파상 전)")
    print("=" * 60)
    _print_board(board_before)
    
    print("\n[2단계] 앙파상 후 상태를 인식 중...")
    detected_move = detect_move_via_ml_capture()
    
    if detected_move:
        print(f"\n✅ 인식 성공: {detected_move.uci()}")
        print(f"   SAN: {game_state.current_board.san(detected_move)}")
        
        # 이동 적용
        game_state.current_board.push(detected_move)
        
        # 이동 적용 후 보드 상태 출력
        print("\n" + "=" * 60)
        print("이후 보드 상태 (앙파상 후 - 이동 적용)")
        print("=" * 60)
        _print_board(game_state.current_board)
        print("=" * 60)
        
        # 보드 되돌리기 (테스트용)
        game_state.current_board.pop()
        
        if board_before.is_en_passant(detected_move):
            print("\n   ✅ 앙파상으로 올바르게 인식됨!")
            return True
        else:
            print("\n   ❌ 앙파상으로 인식되지 않음")
            return False
    else:
        print("\n❌ 인식 실패")
        # 실패해도 보드 상태는 출력
        print("\n" + "=" * 60)
        print("현재 보드 상태 (인식 실패)")
        print("=" * 60)
        _print_board(board_before)
        print("=" * 60)
        return False


def initialize_camera_and_ml():
    """카메라와 ML 모델 초기화"""
    print("[→] 카메라와 ML 모델 초기화 중...\n")
    
    # 카메라 초기화
    if game_state.cv_capture_wrapper is None:
        try:
            print("[→] USB 카메라 초기화 중...")
            game_state.cv_capture = USBCapture(rotate_90_cw=False, rotate_90_ccw=False, rotate_180=True)
            game_state.cv_capture_wrapper = ThreadSafeCapture(game_state.cv_capture)
            print(f"[✓] USB 카메라 캡처 초기화 완료 (/dev/video{game_state.cv_capture.index})")
        except Exception as exc:
            game_state.cv_capture = None
            game_state.cv_capture_wrapper = None
            print(f"[!] USB 카메라 초기화 실패: {exc}")
            return False
    
    # ML 모델 초기화
    if game_state.ml_detector is None:
        try:
            from aicv.ml_piece_detector import ChessPieceMLDetector
            # 모델 경로 찾기 (여러 경로 시도)
            possible_paths = [
                BASE_DIR / "aicv" / "models" / "chess_piece_model.pt",  # brain/aicv/models/
                BASE_DIR.parent / "aicv" / "models" / "chess_piece_model.pt",  # aicv/models/
            ]
            
            model_path = None
            for path in possible_paths:
                if path.exists():
                    model_path = path
                    break
            
            if model_path and model_path.exists():
                print(f"[→] ML 모델 로드 중: {model_path}")
                game_state.ml_detector = ChessPieceMLDetector(str(model_path))
                print(f"[✓] ML 기물 인식 모델 로드 완료 (device: {game_state.ml_detector.device})")
            else:
                print(f"[!] ML 모델 파일을 찾을 수 없습니다.")
                print("   시도한 경로:")
                for path in possible_paths:
                    print(f"   - {path} {'(존재함)' if path.exists() else '(없음)'}")
                return False
        except ImportError:
            print("[!] PyTorch가 설치되지 않아 ML 기물 인식을 사용할 수 없습니다.")
            print("   pip install torch torchvision")
            return False
        except Exception as exc:
            print(f"[!] ML 모델 초기화 실패: {exc}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n✅ 카메라와 ML 모델 초기화 완료\n")
    return True


def main_physical():
    """물리적 체스판 테스트 모드"""
    print("\n" + "=" * 60)
    print("물리적 체스판 테스트 모드 (인터랙티브)")
    print("=" * 60)
    print("\n이 모드는 실제 체스판에서 캐슬링/앙파상을 테스트합니다.")
    print("카메라와 ML 모델이 초기화되어 있어야 합니다.\n")
    
    # ML 모델과 카메라 초기화
    if not initialize_camera_and_ml():
        print("\n❌ 초기화 실패 - 테스트를 진행할 수 없습니다.")
        return 1
    
    print("✅ ML 모델과 카메라 준비 완료\n")
    
    # 테스트 선택
    print("테스트할 항목을 선택하세요:")
    print("1. 흰색 킹사이드 캐슬링")
    print("2. 검은색 퀸사이드 캐슬링")
    print("3. 흰색 앙파상")
    print("4. 검은색 앙파상")
    print("5. 모두 테스트")
    print("0. 종료")
    
    choice = input("\n선택 (0-5): ").strip()
    
    results = []
    
    if choice == "1":
        results.append(("흰색 킹사이드 캐슬링", test_castling_kingside_white_physical()))
    elif choice == "2":
        results.append(("검은색 퀸사이드 캐슬링", test_castling_queenside_black_physical()))
    elif choice == "3":
        results.append(("흰색 앙파상", test_en_passant_white_physical()))
    elif choice == "4":
        results.append(("검은색 앙파상", test_en_passant_black_physical()))
    elif choice == "5":
        results.append(("흰색 킹사이드 캐슬링", test_castling_kingside_white_physical()))
        results.append(("검은색 퀸사이드 캐슬링", test_castling_queenside_black_physical()))
        results.append(("흰색 앙파상", test_en_passant_white_physical()))
        results.append(("검은색 앙파상", test_en_passant_black_physical()))
    elif choice == "0":
        print("종료합니다.")
        return 0
    else:
        print("잘못된 선택입니다.")
        return 1
    
    # 결과 요약
    if results:
        print("\n" + "=" * 60)
        print("테스트 결과 요약")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, result in results:
            status = "✅ 통과" if result else "❌ 실패"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print(f"\n총 {len(results)}개 테스트 중 {passed}개 통과, {failed}개 실패")
    
    return 0


def main():
    """메인 함수 - 모드 선택"""
    print("\n" + "=" * 60)
    print("캐슬링 및 앙파상 인식 테스트")
    print("=" * 60)
    print("\n테스트 모드를 선택하세요:")
    print("1. 시뮬레이션 모드 (카메라 불필요, 빠른 테스트)")
    print("2. 물리적 체스판 모드 (카메라 필요, 실제 보드 테스트)")
    
    mode = input("\n선택 (1/2): ").strip()
    
    if mode == "2":
        return main_physical()
    
    # 시뮬레이션 모드
    print("\n시뮬레이션 모드로 실행합니다...\n")
    
    results = []
    
    # 테스트 실행
    results.append(("흰색 킹사이드 캐슬링", test_castling_kingside_white()))
    results.append(("검은색 퀸사이드 캐슬링", test_castling_queenside_black()))
    results.append(("흰색 앙파상", test_en_passant_white()))
    results.append(("검은색 앙파상", test_en_passant_black()))
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n총 {len(results)}개 테스트 중 {passed}개 통과, {failed}개 실패")
    
    if failed == 0:
        print("\n🎉 모든 테스트 통과!")
        return 0
    else:
        print(f"\n⚠️  {failed}개 테스트 실패 - CV 인식 로직을 확인하세요")
        return 1


if __name__ == "__main__":
    sys.exit(main())
