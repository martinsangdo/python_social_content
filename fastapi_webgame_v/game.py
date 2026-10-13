"""Stateless match-3 engine. Every function works on a board passed in by the caller."""

import random

SIZE = 8
KINDS = 6
POINTS_PER_GEM = 10

Board = list[list[int]]
Pos = tuple[int, int]


def find_matches(board: Board) -> set[Pos]:
    """Every cell that sits in a horizontal or vertical run of 3+ equal gems."""
    matched: set[Pos] = set()
    for r in range(SIZE):
        for c in range(SIZE):
            kind = board[r][c]
            if c + 2 < SIZE and board[r][c + 1] == kind == board[r][c + 2]:
                matched |= {(r, c), (r, c + 1), (r, c + 2)}
            if r + 2 < SIZE and board[r + 1][c] == kind == board[r + 2][c]:
                matched |= {(r, c), (r + 1, c), (r + 2, c)}
    return matched


def _swapped(board: Board, a: Pos, b: Pos) -> Board:
    out = [row[:] for row in board]
    out[a[0]][a[1]], out[b[0]][b[1]] = out[b[0]][b[1]], out[a[0]][a[1]]
    return out


def has_move(board: Board) -> bool:
    for r in range(SIZE):
        for c in range(SIZE):
            for nr, nc in ((r, c + 1), (r + 1, c)):
                if nr < SIZE and nc < SIZE and find_matches(_swapped(board, (r, c), (nr, nc))):
                    return True
    return False


def new_board() -> Board:
    """Random board with no ready-made matches and at least one possible move."""
    while True:
        board: Board = []
        for r in range(SIZE):
            row: list[int] = []
            for c in range(SIZE):
                banned = set()
                if c >= 2 and row[c - 1] == row[c - 2]:
                    banned.add(row[c - 1])
                if r >= 2 and board[r - 1][c] == board[r - 2][c]:
                    banned.add(board[r - 1][c])
                row.append(random.choice([k for k in range(KINDS) if k not in banned]))
            board.append(row)
        if has_move(board):
            return board


def _collapse(board: Board, cleared: set[Pos]) -> Board:
    """Drop surviving gems down each column and fill the gaps from the top."""
    out = [[0] * SIZE for _ in range(SIZE)]
    for c in range(SIZE):
        column = [board[r][c] for r in range(SIZE) if (r, c) not in cleared]
        column = [random.randrange(KINDS) for _ in range(SIZE - len(column))] + column
        for r in range(SIZE):
            out[r][c] = column[r]
    return out


def play_move(board: Board, a: Pos, b: Pos) -> dict | None:
    """Swap a and b, then resolve cascades.

    Returns None if the swap is illegal (not adjacent, or makes no match).
    Otherwise returns {"steps": [{"cleared", "points", "board"}, ...], "board", "shuffled"}.
    """
    if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
        return None
    board = _swapped(board, a, b)
    steps = []
    while matched := find_matches(board):
        board = _collapse(board, matched)
        steps.append(
            {
                "cleared": sorted(matched),
                "points": len(matched) * POINTS_PER_GEM * (len(steps) + 1),
                "board": board,
            }
        )
    if not steps:
        return None
    shuffled = not has_move(board)
    if shuffled:
        board = new_board()
    return {"steps": steps, "board": board, "shuffled": shuffled}
