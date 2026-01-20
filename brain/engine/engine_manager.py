#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stockfish 엔진 매니저
- 엔진 초기화/종료 관리
- 포지션 평가(승률/점수) 제공
- 최선 수 계산 및 적용 유틸
"""

import os
import math
import threading
import chess
import chess.engine
STOCKFISH_PATH = '/usr/games/stockfish'
#STOCKFISH_PATH = '/opt/homebrew/bin/stockfish'


class _EngineManager:
    def __init__(self):
        self._engine = None
        self._ponder_thread = None
        self._ponder_stop_event = threading.Event()
        self._ponder_result = None
        self._ponder_lock = threading.Lock()

    def ensure_engine(self) -> bool:
        if self._engine is not None:
            return True
        if not os.path.exists(STOCKFISH_PATH):
            print(f"[!] Stockfish를 찾을 수 없습니다: {STOCKFISH_PATH}")
            return False
        try:
            self._engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
            # Skill Level을 최고(20)로 설정 (depth와 독립적으로 작동)
            self._engine.configure({"Skill Level": 20})
            print("[✓] Stockfish Skill Level: 20 (최고)")
            return True
        except Exception as e:
            print(f"[!] Stockfish 초기화 실패: {e}")
            self._engine = None
            return False

    def quit(self):
        # Ponder 중지
        self.stop_ponder()
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None
    
    def start_ponder(self, board: chess.Board, depth: int = 10):
        """플레이어가 생각하는 동안 백그라운드에서 다음 수를 미리 계산 (Ponder)"""
        if not self.ensure_engine():
            return False
        
        # 기존 ponder 중지
        self.stop_ponder()
        
        # 새로운 ponder 시작
        self._ponder_stop_event.clear()
        self._ponder_result = None
        
        def _ponder_worker():
            try:
                # 백그라운드에서 분석 시작
                print("[Ponder] 백그라운드 계산 시작...")
                analysis = self._engine.analyse(
                    board, 
                    chess.engine.Limit(depth=depth),
                    info=chess.engine.INFO_ALL
                )
                
                # 중지 신호 확인
                if not self._ponder_stop_event.is_set():
                    with self._ponder_lock:
                        self._ponder_result = analysis
                    print("[Ponder] 백그라운드 계산 완료")
                else:
                    print("[Ponder] 백그라운드 계산 중단됨")
            except Exception as e:
                print(f"[Ponder] 오류: {e}")
        
        self._ponder_thread = threading.Thread(target=_ponder_worker, daemon=True)
        self._ponder_thread.start()
        return True
    
    def stop_ponder(self):
        """Ponder 중지"""
        if self._ponder_thread is not None and self._ponder_thread.is_alive():
            self._ponder_stop_event.set()
            self._ponder_thread.join(timeout=1.0)
            self._ponder_thread = None
            print("[Ponder] 중지됨")
        
        with self._ponder_lock:
            self._ponder_result = None

    @staticmethod
    def _cp_to_win_prob_white(cp: int) -> float:
        # 간단한 로지스틱: 1 / (1 + 10^(-cp/400))
        try:
            return 1.0 / (1.0 + math.pow(10.0, -cp / 400.0))
        except Exception:
            return 0.5

    def evaluate(self, board: chess.Board, depth: int = 10):
        """포지션 평가: cp/mate/백승률/추천수"""
        if not self.ensure_engine():
            return None
        
        start_time = time.time()
        print(f"[Engine] 포지션 분석 시작... (depth={depth})")
        
        try:
            info = self._engine.analyse(board, chess.engine.Limit(depth=depth))
            elapsed = (time.time() - start_time) * 1000
            print(f"[Engine] 포지션 분석 완료 ({elapsed:.1f}ms)")
            
            score = info.get('score')
            bestmove = info.get('pv', [None])[0]

            cp = None
            mate = None
            win_prob_white = None

            if score is not None:
                # 백 관점 점수
                pov = score.white()
                if pov.is_mate():
                    mate = pov.mate()
                    win_prob_white = 1.0 if mate and mate > 0 else 0.0
                else:
                    cp = pov.score(mate_score=100000)
                    win_prob_white = self._cp_to_win_prob_white(cp)

            san = None
            move_type = None
            if bestmove is not None and isinstance(bestmove, chess.Move):
                try:
                    san = board.san(bestmove)
                except Exception:
                    san = bestmove.uci() if bestmove else None
                
                # 움직임의 종류 분석
                move_type = self._analyze_move_type(board, bestmove)

            return {
                'cp': cp,
                'mate': mate,
                'win_prob_white': win_prob_white,
                'best_move': bestmove.uci() if isinstance(bestmove, chess.Move) else None,
                'best_move_san': san,
                'move_type': move_type,
            }
        except Exception as e:
            print(f"[!] 평가 실패: {e}")
            return None

    def _analyze_move_type(self, board: chess.Board, move: chess.Move) -> dict:
        """움직임의 종류를 분석하여 상세 정보 반환"""
        move_info = {
            'is_capture': False,
            'is_castling': False,
            'is_en_passant': False,
            'is_promotion': False,
            'is_check': False,
            'piece_type': None,
            'captured_piece': None,
            'promotion_piece': None
        }
        
        try:
            # 기물 잡기 여부
            if board.is_capture(move):
                move_info['is_capture'] = True
                # 잡힌 기물 확인
                captured_square = move.to_square
                if board.is_en_passant(move):
                    # 앙파상인 경우 잡힌 폰의 위치
                    captured_square = move.from_square + (8 if board.turn else -8)
                move_info['captured_piece'] = board.piece_at(captured_square)
            
            # 앙파상 여부
            if board.is_en_passant(move):
                move_info['is_en_passant'] = True
            
            # 캐슬링 여부
            if board.is_castling(move):
                move_info['is_castling'] = True
            
            # 프로모션 여부
            if move.promotion:
                move_info['is_promotion'] = True
                move_info['promotion_piece'] = move.promotion
            
            # 움직이는 기물 타입
            piece = board.piece_at(move.from_square)
            if piece:
                move_info['piece_type'] = piece.piece_type
            
            # 체크 여부 (움직임을 실행해서 확인)
            board_copy = board.copy()
            board_copy.push(move)
            move_info['is_check'] = board_copy.is_check()
            
        except Exception as e:
            print(f"[!] 움직임 분석 실패: {e}")
        
        return move_info

    def play_best(self, board: chess.Board, depth: int = 10, use_ponder: bool = True):
        """최선 수 실행. 성공 시 (move, san) 반환
        
        Args:
            board: 현재 체스 보드
            depth: 탐색 깊이
            use_ponder: Ponder 결과를 사용할지 여부
        """
        if not self.ensure_engine():
            return None
        
        start_time = time.time()
        
        # Ponder 결과 확인
        ponder_move = None
        if use_ponder:
            with self._ponder_lock:
                if self._ponder_result is not None:
                    # Ponder 결과에서 최선 수 추출
                    pv = self._ponder_result.get('pv', [])
                    if pv and len(pv) > 0:
                        ponder_move = pv[0]
                        elapsed = (time.time() - start_time) * 1000
                        print(f"[Ponder] ⚡ 저장된 결과 사용 (즉시 응답, {elapsed:.1f}ms)")
                else:
                    print(f"[Ponder] ⏳ Ponder 결과 없음 - 새로 계산 필요 (depth={depth})")
        
        # Ponder 결과가 있고 현재 보드와 일치하면 사용
        if ponder_move and isinstance(ponder_move, chess.Move):
            if ponder_move in board.legal_moves:
                try:
                    san = board.san(ponder_move)
                except Exception:
                    san = ponder_move.uci()
                board.push(ponder_move)
                print(f"[Ponder] ✅ Ponder 결과 적용: {ponder_move.uci()} (SAN: {san})")
                return ponder_move, san
        
        # Ponder 결과가 없거나 유효하지 않으면 새로 계산
        try:
            calc_start = time.time()
            print("[Ponder] 🔄 새로 계산 시작...")
            result = self._engine.play(board, chess.engine.Limit(depth=depth))
            calc_elapsed = (time.time() - calc_start) * 1000
            
            if result and result.move:
                move = result.move
                try:
                    san = board.san(move)
                except Exception:
                    san = move.uci()
                board.push(move)
                total_elapsed = (time.time() - start_time) * 1000
                print(f"[Ponder] ✅ 새 계산 완료 (계산: {calc_elapsed:.1f}ms, 총: {total_elapsed:.1f}ms)")
                return move, san
            return None
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            print(f"[!] 엔진 수 계산 실패 ({elapsed:.1f}ms): {e}")
            return None


_manager = _EngineManager()


def init_engine() -> bool:
    return _manager.ensure_engine()


def shutdown_engine():
    _manager.quit()


def evaluate_position(board: chess.Board, depth: int = 10):
    return _manager.evaluate(board, depth)


def engine_make_best_move(board: chess.Board, depth: int = 10, use_ponder: bool = True):
    return _manager.play_best(board, depth, use_ponder)


def start_ponder(board: chess.Board, depth: int = 10):
    """플레이어가 생각하는 동안 백그라운드에서 다음 수를 미리 계산"""
    return _manager.start_ponder(board, depth)


def stop_ponder():
    """Ponder 중지"""
    _manager.stop_ponder()


