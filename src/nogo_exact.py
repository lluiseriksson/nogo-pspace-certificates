"""Pure-stdlib exact combinatorial game engine for Paper 34:
Winning and Losing NoGo is PSPACE-Complete
(Kyle Burke, Alfie Davies, & Craig Tennenhouse, arXiv:2611.33127, Nov 24, 2026).

Implements exact zero-float Graph NoGo, 2D Grid NoGo, normal & misere minimax,
empty-board reachability replay, Coins-are-Lava exact minimax, and connected
bipartite subcubic graph auditing.

Author: Lluis Eriksson
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Sequence, Set, Tuple

# Stone encoding: 0 = Empty, 1 = Black, 2 = White


def grid_graph(rows: int, cols: int) -> Tuple[int, List[List[int]]]:
    """Build orthogonal 4-neighbor adjacency list for a rows x cols square grid."""
    V = rows * cols
    adj: List[List[int]] = [[] for _ in range(V)]
    for r in range(rows):
        for c in range(cols):
            u = r * cols + c
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    adj[u].append(nr * cols + nc)
    return V, adj


def graph_from_edges(num_verts: int, edges: Sequence[Tuple[int, int]]) -> List[List[int]]:
    """Build simple undirected adjacency list from edge list."""
    adj: List[List[int]] = [[] for _ in range(num_verts)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    return adj


def group_has_liberty(board: Sequence[int], adj: Sequence[Sequence[int]], start: int) -> bool:
    """Exact BFS checking whether the same-color connected component containing `start`
    has at least one adjacent empty vertex (liberty)."""
    color = board[start]
    if color == 0:
        return True
    seen = {start}
    q = deque([start])
    while q:
        u = q.popleft()
        for nb in adj[u]:
            st = board[nb]
            if st == 0:
                return True
            if st == color and nb not in seen:
                seen.add(nb)
                q.append(nb)
    return False


def is_legal_nogo_position(board: Sequence[int], adj: Sequence[Sequence[int]]) -> bool:
    """Every occupied group of either color must have at least one liberty."""
    visited: Set[int] = set()
    for v, col in enumerate(board):
        if col == 0 or v in visited:
            continue
        # BFS component
        comp = {v}
        q = deque([v])
        has_lib = False
        while q:
            u = q.popleft()
            for nb in adj[u]:
                if board[nb] == 0:
                    has_lib = True
                elif board[nb] == col and nb not in comp:
                    comp.add(nb)
                    q.append(nb)
        if not has_lib:
            return False
        visited.update(comp)
    return True


def is_legal_nogo_move(board: Sequence[int], adj: Sequence[Sequence[int]], vertex: int, color: int) -> bool:
    """A NoGo move placing `color` (1 or 2) at empty `vertex` is legal iff placing it
    leaves `vertex`'s group AND every adjacent opponent group with >= 1 liberty (no suicide, no capture)."""
    if board[vertex] != 0:
        return False
    nxt = list(board)
    nxt[vertex] = color
    if not group_has_liberty(nxt, adj, vertex):
        return False
    opp = 2 if color == 1 else 1
    for nb in adj[vertex]:
        if nxt[nb] == opp and not group_has_liberty(nxt, adj, nb):
            return False
    return True


def legal_nogo_moves(board: Sequence[int], adj: Sequence[Sequence[int]], color: int) -> List[int]:
    """Return sorted list of all legal NoGo vertices for `color`."""
    return [v for v in range(len(board)) if board[v] == 0 and is_legal_nogo_move(board, adj, v, color)]


def solve_nogo_minimax(
    board: Tuple[int, ...],
    adj: Sequence[Sequence[int]],
    to_move: int,
    misere: bool = False,
) -> Tuple[int, int | None, int]:
    """Exact zero-float minimax solver for Graph/Grid NoGo (normal or misere play).
    Returns (winner_color 1_or_2, winning_first_move_or_None, states_evaluated)."""
    memo: Dict[Tuple[Tuple[int, ...], int], Tuple[int, int | None]] = {}
    states = 0

    def dfs(state: Tuple[int, ...], player: int) -> Tuple[int, int | None]:
        nonlocal states
        key = (state, player)
        if key in memo:
            return memo[key]
        states += 1
        opp = 2 if player == 1 else 1
        moves = legal_nogo_moves(state, adj, player)
        if not moves:
            # Normal play: current player with no legal moves LOSES (opp wins).
            # Misere play: current player with no legal moves WINS (player wins).
            winner = player if misere else opp
            memo[key] = (winner, None)
            return winner, None
        for mv in moves:
            nxt = list(state)
            nxt[mv] = player
            w, _ = dfs(tuple(nxt), opp)
            if w == player:
                memo[key] = (player, mv)
                return player, mv
        memo[key] = (opp, None)
        return opp, None

    win, best_mv = dfs(board, to_move)
    return win, best_mv, states


def solve_coins_are_lava_minimax(
    num_coins: int,
    strings: Sequence[Tuple[int, int]],
    to_move: int = 1,
) -> Tuple[int, int | None, int]:
    """Exact zero-float minimax solver for Coins-are-Lava (Section 4, Lemma 4.1).
    Each string is an edge (u, v) (multiedges allowed). Cutting string `idx` is legal
    iff deg(u) >= 2 and deg(v) >= 2 in the remaining multigraph. Normal play: player
    unable to cut loses. Returns (winner 1_or_2, winning_first_string_idx_or_None, states)."""
    m = len(strings)
    init_mask = (1 << m) - 1
    memo: Dict[Tuple[int, int], Tuple[int, int | None]] = {}
    states = 0

    def degrees(mask: int) -> List[int]:
        deg = [0] * num_coins
        for i in range(m):
            if (mask >> i) & 1:
                u, v = strings[i]
                deg[u] += 1
                deg[v] += 1
        return deg

    def dfs(mask: int, player: int) -> Tuple[int, int | None]:
        nonlocal states
        key = (mask, player)
        if key in memo:
            return memo[key]
        states += 1
        opp = 2 if player == 1 else 1
        deg = degrees(mask)
        # Deduplicate equivalent parallel strings between the same pair {u, v} to keep solver exact & fast
        seen_pairs: Set[Tuple[int, int]] = set()
        legal_indices: List[int] = []
        for i in range(m):
            if (mask >> i) & 1:
                u, v = strings[i]
                if deg[u] >= 2 and deg[v] >= 2:
                    pair = (u, v) if u <= v else (v, u)
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        legal_indices.append(i)
        if not legal_indices:
            memo[key] = (opp, None)
            return opp, None
        for idx in legal_indices:
            w, _ = dfs(mask & ~(1 << idx), opp)
            if w == player:
                memo[key] = (player, idx)
                return player, idx
        memo[key] = (opp, None)
        return opp, None

    win, mv = dfs(init_mask, to_move)
    return win, mv, states


def check_connected_bipartite_subcubic(
    num_verts: int, edges: Sequence[Tuple[int, int]]
) -> Tuple[bool, int, List[int]]:
    """Verify graph is simple, connected, bipartite (2-colorable), and subcubic (max degree <= 3).
    Returns (ok, max_degree, 2_coloring)."""
    if num_verts < 1:
        return False, 0, []
    seen_e: Set[Tuple[int, int]] = set()
    adj: List[List[int]] = [[] for _ in range(num_verts)]
    for u, v in edges:
        if u == v or not (0 <= u < num_verts) or not (0 <= v < num_verts):
            return False, 0, []
        e = (u, v) if u < v else (v, u)
        if e in seen_e:
            return False, 0, []
        seen_e.add(e)
        adj[u].append(v)
        adj[v].append(u)

    max_deg = max(len(nb) for nb in adj)
    if max_deg > 3:
        return False, max_deg, []

    color = [-1] * num_verts
    color[0] = 0
    q = deque([0])
    while q:
        u = q.popleft()
        for nb in adj[u]:
            if color[nb] == -1:
                color[nb] = 1 - color[u]
                q.append(nb)
            elif color[nb] == color[u]:
                return False, max_deg, []
    if any(c == -1 for c in color):
        return False, max_deg, []
    return True, max_deg, color
