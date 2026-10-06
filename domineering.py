#!/usr/bin/env python3
"""Domineering（多米诺棋）——纯标准库实现。

规则：8x8 棋盘，竖方（V）只能放竖向多米诺（占上下相邻两格），
横方（H）只能放横向多米诺（占左右相邻两格）。轮流放子，
轮到谁时无子可放则判负。

    python3 -m domineering                 # 人机对战（人类默认执竖方先手）
    python3 -m domineering --side h        # 人类执横方（AI 先手）
    python3 -m domineering --auto --games 20 --seed 42   # AI 对 AI 自动演示
"""

import argparse
import random
import sys

N = 8
VERT, HORIZ = "V", "H"          # V: 竖方（先手）, H: 横方（后手）

EMPTY, FULL = 0, 1


def new_board():
    """返回 8x8 空棋盘。"""
    return [[EMPTY] * N for _ in range(N)]


def legal_moves(board, player):
    """返回 player 的全部合法走法，每步为 (r1, c1, r2, c2)。"""
    moves = []
    for r in range(N):
        for c in range(N):
            if board[r][c] != EMPTY:
                continue
            if player == VERT:
                if r + 1 < N and board[r + 1][c] == EMPTY:
                    moves.append((r, c, r + 1, c))
            else:  # HORIZ
                if c + 1 < N and board[r][c + 1] == EMPTY:
                    moves.append((r, c, r, c + 1))
    return moves


def place(board, move, player):
    """在棋盘上落子；走法非法（含方向不符/重叠/越界）时抛 ValueError。

    返回新棋盘（不修改原棋盘）。
    """
    r1, c1, r2, c2 = move
    for r, c in ((r1, c1), (r2, c2)):
        if not (0 <= r < N and 0 <= c < N):
            raise ValueError(f"落子越界：{(r1, c1, r2, c2)}")
    if player == VERT:
        if not (c1 == c2 and abs(r1 - r2) == 1):
            raise ValueError(f"竖方只能放竖向多米诺：{(r1, c1, r2, c2)}")
    else:
        if not (r1 == r2 and abs(c1 - c2) == 1):
            raise ValueError(f"横方只能放横向多米诺：{(r1, c1, r2, c2)}")
    if board[r1][c1] != EMPTY or board[r2][c2] != EMPTY:
        raise ValueError(f"落子与已有棋子重叠：{(r1, c1, r2, c2)}")
    b = [row[:] for row in board]
    b[r1][c1] = FULL
    b[r2][c2] = FULL
    return b


def winner(board, to_move):
    """若轮到走棋的一方无子可放，返回另一方；否则返回 None。"""
    if not legal_moves(board, to_move):
        return HORIZ if to_move == VERT else VERT
    return None


def opponent(player):
    return HORIZ if player == VERT else VERT


def ai_move(board, player, rng):
    """贪心 AI：1 步前瞻，最大化（己方后续走法数 − 对方后续走法数）。

    平局随机打破（用传入的 rng，保证 --seed 可复现）。
    """
    moves = legal_moves(board, player)
    if not moves:
        return None
    opp = opponent(player)
    scored = []
    for m in moves:
        b2 = apply_quiet(board, m)
        score = len(legal_moves(b2, player)) - len(legal_moves(b2, opp))
        scored.append((score, m))
    best_score = max(s for s, _ in scored)
    tied = [m for s, m in scored if s == best_score]
    return rng.choice(tied)


def apply_quiet(board, move):
    """内部用：不做方向校验的落子（AI 生成的走法保证合法）。"""
    r1, c1, r2, c2 = move
    b = [row[:] for row in board]
    b[r1][c1] = FULL
    b[r2][c2] = FULL
    return b


# ---------- 显示与输入 ----------

def cell_name(r, c):
    return f"{chr(ord('a') + c)}{r + 1}"


def move_name(move):
    return f"{cell_name(move[0], move[1])} {cell_name(move[2], move[3])}"


def render(board):
    lines = ["   " + " ".join(chr(ord("a") + c) for c in range(N))]
    for r in range(N):
        row = [f"{r + 1:>2} "]
        for c in range(N):
            row.append("■ " if board[r][c] == FULL else "· ")
        lines.append("".join(row))
    return "\n".join(lines)


def parse_cell(text):
    text = text.strip().lower()
    if len(text) < 2 or len(text) > 3 or not text[0].isalpha():
        raise ValueError(f"格子格式错误：{text!r}（示例：d4）")
    c = ord(text[0]) - ord("a")
    r = int(text[1:]) - 1
    if not (0 <= r < N and 0 <= c < N):
        raise ValueError(f"格子越界：{text!r}")
    return r, c


def parse_move(text):
    parts = text.strip().split()
    if len(parts) != 2:
        raise ValueError("请输入两个格子，例如：d4 d5")
    (r1, c1), (r2, c2) = parse_cell(parts[0]), parse_cell(parts[1])
    return (r1, c1, r2, c2)


def side_name(player):
    return "竖方（V，先手）" if player == VERT else "横方（H，后手）"


# ---------- 对局 ----------

def play_auto(games, seed, verbose=False):
    """AI 对 AI，返回 (v_wins, h_wins)。"""
    v_wins = h_wins = 0
    for g in range(games):
        rng = random.Random(None if seed is None else seed + g)
        board = new_board()
        to_move = VERT
        ply = 0
        while True:
            w = winner(board, to_move)
            if w is not None:
                break
            m = ai_move(board, to_move, rng)
            board = apply_quiet(board, m)
            to_move = opponent(to_move)
            ply += 1
        if w == VERT:
            v_wins += 1
        else:
            h_wins += 1
        if verbose:
            print(f"第 {g + 1}/{games} 局：{side_name(w)}胜，用时 {ply} 手")
    return v_wins, h_wins


def play_interactive(human_side):
    ai_side = opponent(human_side)
    rng = random.Random()
    board = new_board()
    to_move = VERT
    print("=== Domineering 多米诺棋 ===")
    print("竖方放竖向多米诺，横方放横向多米诺；无子可放者输。")
    print(f"你执{side_name(human_side)}。走法示例：d4 d5（两个相邻格）")
    print()
    while True:
        w = winner(board, to_move)
        if w is not None:
            print(render(board))
            print()
            if w == human_side:
                print("🎉 你赢了！")
            else:
                print("😅 AI 赢了。")
            return
        if to_move == human_side:
            print(render(board))
            print(f"轮到你（{side_name(human_side)}），合法走法 {len(legal_moves(board, human_side))} 种")
            try:
                text = input("你的走法（q 退出）：")
            except EOFError:
                print("\n结束。")
                return
            if text.strip().lower() in ("q", "quit", "exit"):
                print("结束。")
                return
            try:
                m = parse_move(text)
                board = place(board, m, human_side)
            except ValueError as e:
                print(f"❌ {e}，请重试。")
                continue
        else:
            m = ai_move(board, ai_side, rng)
            board = apply_quiet(board, m)
            print(f"AI（{side_name(ai_side)}）走：{move_name(m)}")
        to_move = opponent(to_move)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Domineering 多米诺棋（纯标准库）")
    ap.add_argument("--auto", action="store_true", help="AI 对 AI 自动演示")
    ap.add_argument("--games", type=int, default=10, help="自动演示局数（默认 10）")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--side", choices=["v", "h"], default="v",
                    help="人机对战时人类执子：v 竖方（先手），h 横方（后手）")
    ap.add_argument("--verbose", action="store_true", help="自动演示时逐局打印")
    args = ap.parse_args(argv)

    if args.auto:
        v_wins, h_wins = play_auto(args.games, args.seed, args.verbose)
        print(f"自动演示结束：共 {args.games} 局，"
              f"竖方（先手）胜 {v_wins}，横方（后手）胜 {h_wins}")
        return 0

    if not sys.stdin.isatty():
        print("交互模式需要终端；无头演示请用 --auto。", file=sys.stderr)
        return 2
    play_interactive(VERT if args.side == "v" else HORIZ)
    return 0


if __name__ == "__main__":
    sys.exit(main())
