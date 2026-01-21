#!/usr/bin/env python3
"""
흑색(로봇팔) 특수 움직임 테스트
- 캐슬링 (킹사이드, 퀸사이드)
- 앙파상
- 프로모션
"""

import sys
import chess
from brain.robot_arm.robot_arm_controller import RobotArmController

class SpecialMoveTester:
    def __init__(self, dry_run=True):
        """
        Args:
            dry_run: True면 명령만 출력, False면 실제 로봇팔 실행
        """
        self.dry_run = dry_run
        if not dry_run:
            self.robot = RobotArmController(enabled=True)
            print("\n🔌 로봇팔 연결 중...")
            if self.robot.connect():
                print("✅ 로봇팔 연결 성공!")
            else:
                print("❌ 로봇팔 연결 실패! 명령만 표시됩니다.")
        else:
            self.robot = None
            
    def setup_board(self, fen):
        """FEN 문자열로 체스판 설정"""
        board = chess.Board(fen)
        print("\n" + "="*60)
        print("📋 현재 보드 상태:")
        print("="*60)
        print(board)
        print(f"\nFEN: {fen}")
        print(f"차례: {'흑색' if board.turn == chess.BLACK else '백색'}")
        return board
    
    def test_move(self, board, move_uci, description):
        """특정 움직임 테스트"""
        print("\n" + "-"*60)
        print(f"🎯 테스트: {description}")
        print(f"📍 이동: {move_uci}")
        print("-"*60)
        
        try:
            move = chess.Move.from_uci(move_uci)
            
            if move not in board.legal_moves:
                print(f"❌ 불가능한 이동입니다!")
                print(f"가능한 이동: {[m.uci() for m in board.legal_moves]}")
                return False
            
            # 이동 타입 분석
            move_type = {
                'is_castling': board.is_castling(move),
                'is_en_passant': board.is_en_passant(move),
                'is_capture': board.is_capture(move),
                'is_promotion': move.promotion is not None
            }
            
            print(f"\n이동 타입:")
            print(f"  - 캐슬링: {move_type['is_castling']}")
            print(f"  - 앙파상: {move_type['is_en_passant']}")
            print(f"  - 잡기: {move_type['is_capture']}")
            print(f"  - 프로모션: {move_type['is_promotion']}")
            
            # 로봇팔 명령 생성
            if self.dry_run:
                # 명령만 생성 (실제 실행 안 함)
                robot_temp = RobotArmController(enabled=False)
                commands = robot_temp._generate_move_commands(move_type, move_uci)
                print(f"\n🤖 생성된 로봇팔 명령:")
                for i, cmd in enumerate(commands, 1):
                    print(f"  {i}. {cmd}")
            else:
                # 실제 로봇팔 실행
                print(f"\n🤖 로봇팔 실행 중...")
                success = self.robot.execute_move(move_type, move_uci)
                if success:
                    print(f"✅ 로봇팔 실행 완료")
                else:
                    print(f"❌ 로봇팔 실행 실패")
                    return False
            
            # 보드에 이동 적용
            board.push(move)
            print(f"\n📋 이동 후 보드:")
            print(board)
            
            return True
            
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("\n" + "="*60)
        print("🧪 흑색(로봇팔) 특수 움직임 테스트")
        print("="*60)
        print(f"모드: {'명령 출력만 (DRY RUN)' if self.dry_run else '실제 로봇팔 실행'}")
        
        # 테스트 1: 킹사이드 캐슬링
        print("\n\n" + "🏰 " * 20)
        print("테스트 1: 흑색 킹사이드 캐슬링 (O-O)")
        print("🏰 " * 20)
        fen1 = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1"
        board1 = self.setup_board(fen1)
        self.test_move(board1, "e8g8", "킹사이드 캐슬링 (e8g8)")
        
        # 테스트 2: 퀸사이드 캐슬링
        print("\n\n" + "🏰 " * 20)
        print("테스트 2: 흑색 퀸사이드 캐슬링 (O-O-O)")
        print("🏰 " * 20)
        fen2 = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1"
        board2 = self.setup_board(fen2)
        self.test_move(board2, "e8c8", "퀸사이드 캐슬링 (e8c8)")
        
        # 테스트 3: 앙파상
        print("\n\n" + "🎣 " * 20)
        print("테스트 3: 흑색 앙파상")
        print("🎣 " * 20)
        # 흑색 폰이 f4에 있고, 백색 폰이 e2에서 e4로 두 칸 이동한 직후
        fen3 = "rnbqkbnr/pppp1ppp/8/8/4Pp2/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        board3 = self.setup_board(fen3)
        self.test_move(board3, "f4e3", "앙파상 (f4e3, e4의 폰 잡기)")
        
        # 테스트 4: 앙파상 (다른 경우)
        print("\n\n" + "🎣 " * 20)
        print("테스트 4: 흑색 앙파상 (왼쪽)")
        print("🎣 " * 20)
        # 흑색 폰이 d4에 있고, 백색 폰이 c2에서 c4로 두 칸 이동한 직후
        fen4 = "rnbqkbnr/pp1ppppp/8/8/2Pp4/8/PP1PPPPP/RNBQKBNR b KQkq c3 0 1"
        board4 = self.setup_board(fen4)
        self.test_move(board4, "d4c3", "앙파상 (d4c3, c4의 폰 잡기)")
        
        # 테스트 5: 프로모션 (퀸)
        print("\n\n" + "👑 " * 20)
        print("테스트 5: 흑색 프로모션 (퀸)")
        print("👑 " * 20)
        # 흑색 폰이 a2에 있고 a1로 이동 가능
        fen5 = "rnbqkbnr/pppppppp/8/8/8/8/p7/4K3 b kq - 0 1"
        board5 = self.setup_board(fen5)
        self.test_move(board5, "a2a1q", "프로모션 (a2a1, 퀸으로)")
        
        # 테스트 6: 프로모션 with 잡기 (퀸)
        print("\n\n" + "👑 " * 20)
        print("테스트 6: 흑색 프로모션 (잡기 + 퀸)")
        print("👑 " * 20)
        # 흑색 폰이 a2에 있고 b1의 나이트를 잡으며 프로모션
        fen6 = "rnbqkbnr/pppppppp/8/8/8/8/p7/1N2K3 b kq - 0 1"
        board6 = self.setup_board(fen6)
        self.test_move(board6, "a2b1q", "프로모션 잡기 (a2b1, 나이트 잡고 퀸으로)")
        
        print("\n\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        
        # 로봇팔 연결 종료
        if not self.dry_run and self.robot:
            print("\n🔌 로봇팔 연결 종료 중...")
            self.robot.disconnect()
            print("✅ 연결 종료 완료")


def main():
    """메인 함수"""
    print("\n흑색(로봇팔) 특수 움직임 테스트 프로그램")
    print("="*60)
    
    # 사용자 선택
    if len(sys.argv) > 1 and sys.argv[1] == "--real":
        print("\n⚠️  실제 로봇팔 실행 모드")
        print("로봇팔이 연결되어 있고 체스판이 준비되었는지 확인하세요!")
        
        # --yes 플래그가 있으면 확인 없이 실행
        if len(sys.argv) > 2 and sys.argv[2] == "--yes":
            print("✅ 자동 확인 모드 - 바로 실행합니다.")
            dry_run = False
        else:
            try:
                response = input("\n계속하시겠습니까? (yes/no): ")
                if response.lower() != 'yes':
                    print("테스트 취소됨")
                    return
                dry_run = False
            except (EOFError, KeyboardInterrupt):
                print("\n❌ 입력을 받을 수 없습니다. --yes 플래그를 사용하세요.")
                print("   예: python3 test_special_moves.py --real --yes")
                return
    else:
        print("\n🔍 DRY RUN 모드 (명령만 출력)")
        print("실제 로봇팔을 실행하려면: python3 test_special_moves.py --real --yes")
        dry_run = True
    
    # 테스트 실행
    tester = SpecialMoveTester(dry_run=dry_run)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
