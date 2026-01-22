from __future__ import annotations

import os
import sys
import select
import time
from typing import Optional

import chess

from game import game_state
from game.board_display import display_board
from cv.cv_detection import (
    detect_move_via_cv,
    detect_move_via_ml_capture,
    initialize_board_reference,
    load_chess_pieces,
)
from cv.cv_manager import save_initial_board_from_capture

from cv.player_input import get_move_from_user
from cv.cv_web import USBCapture, ThreadSafeCapture, start_cv_web_server
from engine.engine_control import get_stockfish_response_move, make_stockfish_move
from engine.engine_manager import init_engine, shutdown_engine, start_ponder, stop_ponder
from game.game_utils import describe_game_end
from robot_arm.robot_arm_controller import (
    connect_robot_arm,
    disconnect_robot_arm,
    get_robot_status,
    init_robot_arm,
    move_robot_to_zero_position,
    test_robot_connection,
)
from robot_arm.robot_control import perform_robot_move, wait_until_robot_idle
from timer.timer_control import (
    check_time_over,
    press_timer_button,
    send_timer_move_command,
    wait_for_timer_completion,
)
from timer.timer_manager import (
    check_timer_button,
    get_chess_timer_status,
    get_timer_manager,
    init_chess_timer,
    send_timer_start,
    send_timer_end,
    send_timer_black,
)


def reset_board_reference() -> bool:
    """현재 카메라 상태를 초기 기준값으로 재설정합니다."""
    if game_state.cv_capture_wrapper is None:
        print("[!] 캡처 장치가 없어 체스판 기준값을 재설정할 수 없습니다")
        return False
    
    print("[→] 체스판 기준값 재설정 중...")
    board_vals, _ = save_initial_board_from_capture(
        game_state.cv_capture_wrapper, str(game_state.BOARD_VALUES_PATH)
    )
    if board_vals is not None:
        game_state.init_board_values = board_vals
        # ML 이전 그리드 초기화
        game_state.ml_previous_grid = None
        print("[✓] 체스판 기준값 재설정 완료")
        print("[✓] ML 이전 상태 초기화 완료")
        return True
    else:
        print("[!] 체스판 기준값 재설정 실패")
        return False


def initialize_game(stockfish_path: str) -> bool:
    """엔진/로봇/타이머/CV 초기화 및 웹 모니터링 시작."""
    print("♔ 터미널 체스 게임 시작 ♔")
    print("=" * 50)

    if not os.path.exists(stockfish_path):
        print(f"[!] Stockfish를 찾을 수 없습니다: {stockfish_path}")
        print("[!] 체스 엔진 기능이 제한됩니다.")
        return False

    init_engine()

    print("[→] 로봇팔 초기화 중...")
    # 포트는 robot_arm_controller.py에서 설정된 기본값 사용
    init_robot_arm(enabled=True, baudrate=9600)

    if test_robot_connection():
        print("[✓] 로봇팔 연결 테스트 성공")
        if connect_robot_arm():
            print("[✓] 로봇팔 연결 완료")
            # 로봇팔을 제로 포지션으로 이동
            print("[→] 로봇팔을 제로 포지션으로 이동 중...")
            move_robot_to_zero_position()
        else:
            print("[!] 로봇팔 연결 실패 - 명령 전송 없이 진행")
    else:
        print("[!] 로봇팔 연결 테스트 실패 - 명령 전송 없이 진행")

    print("[→] 아두이노 타이머 연결 시도 중...")
    if not init_chess_timer():
        print("[!] 아두이노 타이머 연결 실패 - 타이머 없이 진행")
    else:
        print("[✓] 아두이노 타이머 연결 및 모니터링 시작 완료")
        status = get_chess_timer_status()
        print(f"[→] 타이머 상태: {status}")
        # 타이머가 0이면 초기화
        timer_manager = get_timer_manager()
        if timer_manager.black_timer <= 0 or timer_manager.white_timer <= 0:
            print("[→] 타이머가 0이므로 초기화합니다...")
            timer_manager.reset_timers()

    game_state.chess_pieces_state = load_chess_pieces()
    game_state.cv_turn_color = "white"

    try:
        # USB 카메라 기준 캡처 초기화 (자동으로 사용 가능한 장치를 탐색)
        game_state.cv_capture = USBCapture(rotate_90_cw=False, rotate_90_ccw=False, rotate_180=True)
        game_state.cv_capture_wrapper = ThreadSafeCapture(game_state.cv_capture)
        print(f"[✓] USB 카메라 캡처 초기화 완료 (/dev/video{game_state.cv_capture.index})")
    except Exception as exc:
        game_state.cv_capture = None
        game_state.cv_capture_wrapper = None
        print(f"[!] USB 카메라 초기화 실패: {exc}")

    if game_state.cv_capture_wrapper is not None:
        print("[→] 체스판 기준값 초기화(CV) 중...")
        initialize_board_reference()
        
        # ML 기물 인식 모델 초기화
        try:
            from aicv.ml_piece_detector import ChessPieceMLDetector
            model_path = str(game_state.BASE_DIR.parent / "aicv" / "models" / "chess_piece_model.pt")
            if os.path.exists(model_path):
                game_state.ml_detector = ChessPieceMLDetector(model_path)
                print(f"[✓] ML 기물 인식 모델 로드 완료: {model_path}")
            else:
                print(f"[!] ML 모델 파일을 찾을 수 없습니다: {model_path}")
        except ImportError:
            print("[!] PyTorch가 설치되지 않아 ML 기물 인식을 사용할 수 없습니다.")
        except Exception as exc:
            print(f"[!] ML 모델 초기화 실패: {exc}")
    else:
        print("[!] 캡처 장치가 없어 체스판 기준값을 초기화할 수 없습니다")

    import time
    server_start_time = time.time()
    print("[→] CV 웹 서버 초기화 시작...")
    try:
        start_cv_web_server(
            np_path=str(game_state.BOARD_VALUES_PATH),
            pkl_path=str(game_state.CHESS_PIECES_PATH),
            use_thread=True,
            cap=game_state.cv_capture_wrapper,
            port=5003,
        )
        elapsed = (time.time() - server_start_time) * 1000
        print(f"[✓] CV 웹 모니터링 서버 시작 완료 (http://0.0.0.0:5003) - 총 {elapsed:.1f}ms")
    except Exception as exc:
        elapsed = (time.time() - server_start_time) * 1000
        print(f"[!] CV 웹 서버 시작 실패 ({elapsed:.1f}ms): {exc}")

    game_state.player_color = "white"
    print("[→] 플레이어 색상: white (고정)")

    print(f"게임 설정: {game_state.player_color} 플레이어")
    print("[→] 초기 보드 상태 확인 중...")
    print(f"[→] 게임 종료 여부: {game_state.current_board.is_game_over()}")
    print(f"[→] 현재 차례: {'흰색' if game_state.current_board.turn == chess.WHITE else '검은색'}")

    return True


def game_loop() -> None:
    """메인 게임 루프."""
    game_state.difficulty = 10
    print(f"[→] Depth: {game_state.difficulty}, Skill Level: 20 (최고)")
    print(f"게임 설정: {game_state.player_color} 플레이어, Depth {game_state.difficulty}")
    
    # 게임 시작 대기
    print("\n" + "=" * 50)
    print("🎮 게임을 시작하려면 엔터 키를 누르세요...")
    print("=" * 50)
    input()
    
    # 타이머 시작 신호 전송
    print("🚀 게임 시작!")
    send_timer_start()
    print()

    while not game_state.game_over:

        if check_time_over():
            game_state.game_over = True
            break

        display_board()
        print(
            f"[DEBUG] 현재 상태 - 차례: "
            f"{'백' if game_state.current_board.turn == chess.WHITE else '흑'}, "
            f"FEN: {game_state.current_board.fen()}"
        )

        # 흰색/검은색 차례 모두 타이머 버튼 또는 엔터 키 입력 대기 (ML CV로 기물 인식)
        turn_color = "흰색" if game_state.current_board.turn == chess.WHITE else "검은색"
        
        # 플레이어 차례 시작 시 Ponder 시작 (백그라운드에서 다음 수 미리 계산)
        if game_state.current_board.turn == chess.WHITE and game_state.player_color == "white":
            start_ponder(game_state.current_board, depth=game_state.difficulty)
        elif game_state.current_board.turn == chess.BLACK and game_state.player_color == "black":
            start_ponder(game_state.current_board, depth=game_state.difficulty)
        
        if game_state.ml_previous_grid is None:
            print(f"🔘 {turn_color} 차례 - 기물을 이동한 후 타이머 버튼 또는 엔터 키를 누르세요")
            print("   (첫 입력: 초기 상태와 비교, 이후: 이전 상태와 비교)")
        else:
            print(f"🔘 {turn_color} 차례 - 기물을 이동한 후 타이머 버튼 또는 엔터 키를 누르세요")
        print("   (타이머/엔터: CV 인식, 'r': 초기 기준값 재설정, 'q': 종료)")
        
        try:
            # 타이머와 키보드 입력을 동시에 대기
            input_result = _wait_for_input_or_timer()
            
            if input_result is None:
                continue
            
            # 입력 타입 파싱
            if input_result.startswith("timer:"):
                timer_event = input_result[6:]  # "timer:" 제거
                print(f"[TIMER] 타이머 입력 감지: {timer_event}")
                
                if timer_event == "white_turn_end":
                    print("[TIMER] 백 차례 종료 (P2 버튼 눌림) - ML CV 작동 시작")
                    handle_player_turn()
                elif timer_event == "black_turn_end":
                    print("[TIMER] 흑 차례 종료 (P1 버튼 눌림)")
                else:
                    print(f"[TIMER] 기타 신호: {timer_event}")
                    continue
                    
            elif input_result.startswith("input:"):
                user_input = input_result[6:]  # "input:" 제거
                
                if user_input in ['q', 'quit', 'exit']:
                    game_state.game_over = True
                    break
                elif user_input == 'r':
                    # 초기 기준값 재설정
                    print("\n[🔄] 초기 기준값 재설정 시작...")
                    print("[안내] 체스판을 올바른 초기 상태로 배치하세요")
                    if reset_board_reference():
                        print("[✓] 초기 기준값이 재설정되었습니다")
                        print("[→] 다음 입력부터 새로운 기준값으로 비교합니다\n")
                    else:
                        print("[!] 초기 기준값 재설정 실패\n")
                    continue
                
                # 엔터 입력 시 ML CV로 기물 인식
                print("🔘 엔터 입력 감지 - ML CV 작동 시작")
                handle_player_turn()
            
        except KeyboardInterrupt:
            print("\n게임이 중단되었습니다.")
            game_state.game_over = True
            break

        if game_state.game_over:
            break

        if game_state.current_board.is_game_over():
            print("[DEBUG] 게임 종료 조건 만족!")
            print(f"[DEBUG] 체크메이트: {game_state.current_board.is_checkmate()}")
            print(f"[DEBUG] 스테일메이트: {game_state.current_board.is_stalemate()}")
            print(f"[DEBUG] 체크: {game_state.current_board.is_check()}")
            game_state.game_over = True
            break

    display_board()
    print("게임 종료!")
    
    # 타이머 종료 신호 전송
    print("\n⏹️ 타이머 종료...")
    send_timer_end()


def handle_player_turn() -> None:
    """사용자 차례 처리 - 엔터 입력 후 ML CV로 기물 인식."""
    try:
        # CV 방식 - ML 기반 기물 인식 사용 (흰색/검은색 모두)
        move = None
        if game_state.ml_detector is not None:
            # 최대 3번 시도
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                print(f"\n[CV] ML 감지 시도 {attempt}/{max_attempts}")
                move = detect_move_via_ml_capture()
                if move is not None:
                    print(f"[CV] ✅ ML 감지 성공 (시도 {attempt}회)")
                    break
                else:
                    if attempt < max_attempts:
                        print(f"[CV] ⚠️ ML 감지 실패 - 재시도 중... ({attempt}/{max_attempts})")
                        print("[CV] 기물을 정확한 위치에 놓고 잠시 후 자동으로 재시도합니다...")
                        time.sleep(1)  # 1초 대기 후 재시도
                    else:
                        print(f"[CV] ❌ ML 감지 실패 ({max_attempts}회 시도) - 수동 입력으로 전환")
            
            # 3번 시도 후에도 실패하면 수동 입력
            if move is None:
                move = get_move_from_user()
        else:
            # ML detector가 없으면 기존 CV 방식 또는 사용자 입력 사용
            move = detect_move_via_cv()
            if move is None:
                print("[CV] CV 감지 실패 - 사용자 입력으로 대체")
                move = get_move_from_user()
    except Exception as exc:
        print(f"[ERROR] 사용자 입력 처리 실패: {exc}")
        return

    if move == "quit":
        game_state.game_over = True
        return

    if not isinstance(move, chess.Move):
        print("❌ 유효하지 않은 움직임입니다!")
        return

    apply_detected_move(move)
    if game_state.game_over:
        return

    # 플레이어 수 확정 후 Ponder 중지
    stop_ponder()
    
    engine_move = get_stockfish_response_move()
    if engine_move is None:
        print("[Stockfish] 엔진 이동을 생성하지 못했습니다.")
        return

    if not perform_robot_move(engine_move):
        print("[Stockfish] 로봇 이동 실패.")
        return

    # 로봇팔 완료 신호는 perform_robot_move 내부에서 이미 대기함
    print("🤖 로봇팔 이동 완료")
    
    # 로봇이 완전히 멈추고 안정화될 때까지 추가 대기
    time.sleep(1.0)  # 1초 대기
    
    # 로봇이 수를 두고 나서 타이머에 black 신호 전송
    send_timer_black()
    
    apply_detected_move(engine_move)
    
    # 타이머 사용 시 활성화
    # print("타이머로 이동 명령 전송")
    # if send_timer_move_command():
    #     wait_for_timer_completion(timeout=2.0)
    #     print("✅ 타이머 이동 완료")
    # press_timer_button("P1")


def handle_engine_turn() -> None:
    """엔진 차례 처리."""
    try:
        print("🤖 Stockfish가 생각 중...")
        robot_status = get_robot_status()
        if robot_status["is_connected"]:
            wait_until_robot_idle()

        if make_stockfish_move():
            game_state.move_count += 1
            print("✅ Stockfish 이동 완료")
            if check_time_over():
                game_state.game_over = True
            elif game_state.current_board.is_game_over():
                print(
                    f"[DEBUG] 엔진 수 이후 게임 종료: "
                    f"{describe_game_end(game_state.current_board)}"
                )
                game_state.game_over = True
        else:
            print("❌ Stockfish 이동 실패 - 다음 턴으로 계속 진행")
            time.sleep(0.5)
    except Exception as exc:
        print(f"[ERROR] 엔진 차례 처리 실패: {exc}")
        time.sleep(1)


def apply_detected_move(move: chess.Move) -> None:
    """인식된 이동을 보드에 반영하고 종료 여부를 확인."""
    if move is None:
        return

    try:
        # 이동 전에 특수 수 확인
        is_castling_before = game_state.current_board.is_castling(move)
        is_en_passant_before = game_state.current_board.is_en_passant(move)
        is_promotion_before = move.promotion is not None
        
        try:
            san_move = game_state.current_board.san(move)
        except Exception:
            san_move = move.uci()

        # 보드에 이동 적용 (캐슬링의 경우 룩도 자동으로 이동됨)
        game_state.current_board.push(move)
        game_state.move_count += 1

        # CV 방식 메시지
        move_type_str = ""
        if is_castling_before:
            move_type_str = " (캐슬링)"
        elif is_en_passant_before:
            move_type_str = " (앙파상)"
        elif is_promotion_before:
            move_type_str = f" (프로모션: {move.promotion})"
        
        print(f"✅ CV 감지된 이동 적용: {move.uci()} (SAN: {san_move}){move_type_str}")
        
        # 캐슬링인 경우 추가 확인
        if is_castling_before:
            # 이동 후 보드에서 킹과 룩 위치 확인
            if move.to_square == chess.parse_square("g1"):  # 킹사이드 캐슬링
                rook_square = chess.parse_square("f1")
                king_square = chess.parse_square("g1")
            elif move.to_square == chess.parse_square("c1"):  # 퀸사이드 캐슬링
                rook_square = chess.parse_square("d1")
                king_square = chess.parse_square("c1")
            elif move.to_square == chess.parse_square("g8"):  # 검은색 킹사이드
                rook_square = chess.parse_square("f8")
                king_square = chess.parse_square("g8")
            elif move.to_square == chess.parse_square("c8"):  # 검은색 퀸사이드
                rook_square = chess.parse_square("d8")
                king_square = chess.parse_square("c8")
            else:
                rook_square = None
                king_square = move.to_square
            
            if rook_square:
                king = game_state.current_board.piece_at(king_square)
                rook = game_state.current_board.piece_at(rook_square)
                if king and king.piece_type == chess.KING and rook and rook.piece_type == chess.ROOK:
                    print(f"   ✅ 캐슬링 확인: 킹={chess.square_name(king_square)}, 룩={chess.square_name(rook_square)}")
                else:
                    print(f"   ⚠️  캐슬링 후 기물 위치 확인 실패")
        
        # 이동 후 보드 표시
        print("\n" + "="*50)
        display_board()
        print("="*50 + "\n")

        # wait_until_robot_idle() 제거 - perform_robot_move()에서 이미 대기함

        if check_time_over():
            game_state.game_over = True
            return

        if game_state.current_board.is_game_over():
            print(f"[DEBUG] 이동 후 게임 종료: {describe_game_end(game_state.current_board)}")
            game_state.game_over = True
    except Exception as exc:
        print(f"[ERROR] 이동 적용 실패: {exc}")


def cleanup_game() -> None:
    """게임 종료 후 자원 정리."""
    # 타이머 종료 신호 전송 (이미 보냈을 수도 있지만 안전하게 한 번 더)
    try:
        send_timer_end()
    except Exception:
        pass
    
    timer_manager = get_timer_manager()
    if getattr(timer_manager, "is_monitoring", False):
        timer_manager.stop_monitoring()
    if getattr(timer_manager, "is_connected", False):
        timer_manager.disconnect()
    print("아두이노 타이머 연결을 종료했습니다.")

    disconnect_robot_arm()
    print("로봇팔 연결을 종료했습니다.")

    shutdown_engine()

    if game_state.cv_capture_wrapper is not None:
        try:
            game_state.cv_capture_wrapper.release()
        except Exception:
            pass


def _poll_timer_button() -> Optional[str]:
    """타이머 버튼 입력을 감지하고 의미있는 이벤트로 변환."""
    try:
        raw_signal = check_timer_button()
    except Exception as exc:
        print(f"[ERROR] 타이머 입력 확인 실패: {exc}")
        time.sleep(1)
        return None

    if not raw_signal:
        return None

    if raw_signal in ("P1", "P2"):
        return "black_turn_end" if raw_signal == "P1" else "white_turn_end"

    return raw_signal


def _wait_for_input_or_timer() -> Optional[str]:
    """타이머 입력을 지속적으로 체크하면서 사용자 입력을 대기합니다.
    
    Returns:
        'timer:white_turn_end' - 타이머에서 백 차례 종료 신호
        'timer:black_turn_end' - 타이머에서 흑 차례 종료 신호
        'input:...' - 사용자 키보드 입력
        None - 에러 발생
    """
    print("   입력 대기 중... (타이머 버튼 또는 엔터 키 입력)")
    
    while True:
        # 타이머 입력 체크
        timer_input = _poll_timer_button()
        if timer_input:
            return f"timer:{timer_input}"
        
        # 키보드 입력 체크 (논블로킹)
        if select.select([sys.stdin], [], [], 0.1)[0]:
            user_input = sys.stdin.readline().strip().lower()
            return f"input:{user_input}"
        
        # 짧은 대기 (CPU 사용률 감소)
        time.sleep(0.05)

