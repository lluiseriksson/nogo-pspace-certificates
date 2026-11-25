"""Pure-stdlib zero-float verifier for NOGO-PSPACE-CERT-1.0 certificates.
Supports four exact combinatorial game modes aligned with Kyle Burke, Alfie Davies,
& Craig Tennenhouse (arXiv:2611.33127, Nov 24, 2026) "Winning and losing NoGo is PSPACE-complete":
  1. nogo_board_legality_and_reachability (Sec 2 & Thm 1.1: legal n x n grid position + ply-by-ply replay from empty board)
  2. b2cl_gadget_minimax_normal_misere    (Sec 2-3 & Thm 1.1: exact normal & misere minimax on grid NoGo gadgets)
  3. coins_are_lava_exact_minimax         (Sec 4 & Lemma 4.1: exact Coins-are-Lava minimax & parity-win audit)
  4. subcubic_bipartite_graph_nogo        (Sec 4 & Thm 1.2: connected bipartite subcubic Delta<=3 Graph NoGo minimax)

Author: Lluis Eriksson
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from src.nogo_exact import (
    check_connected_bipartite_subcubic,
    graph_from_edges,
    grid_graph,
    is_legal_nogo_move,
    is_legal_nogo_position,
    legal_nogo_moves,
    solve_coins_are_lava_minimax,
    solve_nogo_minimax,
)

SCHEMA_VERSION = "NOGO-PSPACE-CERT-1.0"


class NoGoCertificateError(ValueError):
    """Raised whenever any NOGO-PSPACE-CERT-1.0 verification check fails."""


def _assert_strict_json_types(obj: Any, path: str = "root") -> None:
    t = type(obj)
    if t is int or t is str or obj is None:
        return
    if t is dict:
        for k, v in obj.items():
            if type(k) is not str:
                raise NoGoCertificateError(f"Non-str dict key at {path}")
            _assert_strict_json_types(v, f"{path}.{k}")
        return
    if t is list:
        for i, v in enumerate(obj):
            _assert_strict_json_types(v, f"{path}[{i}]")
        return
    raise NoGoCertificateError(f"Forbidden type {t.__name__} at {path}")


def _parse_int(val: Any, name: str) -> int:
    if type(val) is not int:
        raise NoGoCertificateError(f"{name} must be strict int, got {type(val).__name__}")
    return val


def _parse_board(raw: Any, expected_len: int, name: str) -> Tuple[int, ...]:
    if type(raw) is not list or len(raw) != expected_len:
        raise NoGoCertificateError(f"{name} must be list of length {expected_len}")
    out: List[int] = []
    for i, x in enumerate(raw):
        v = _parse_int(x, f"{name}[{i}]")
        if v not in (0, 1, 2):
            raise NoGoCertificateError(f"{name}[{i}] must be in {{0,1,2}}, got {v}")
        out.append(v)
    return tuple(out)


def _verify_mode1_reachability(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema", "mode", "name", "rows", "cols", "target_board",
        "play_sequence", "claimed_black_moves", "claimed_white_moves",
    }
    if set(cert.keys()) != req:
        raise NoGoCertificateError(f"Mode 1 key mismatch: {sorted(set(cert.keys()) ^ req)}")
    rows = _parse_int(cert["rows"], "rows")
    cols = _parse_int(cert["cols"], "cols")
    if not (2 <= rows <= 12) or not (2 <= cols <= 12):
        raise NoGoCertificateError("Require 2 <= rows, cols <= 12")
    V, adj = grid_graph(rows, cols)
    target = _parse_board(cert["target_board"], V, "target_board")
    if not is_legal_nogo_position(target, adj):
        raise NoGoCertificateError("target_board is not a legal NoGo position (group has 0 liberties)")

    seq = cert["play_sequence"]
    if type(seq) is not list or len(seq) == 0 or len(seq) > V:
        raise NoGoCertificateError("play_sequence must be non-empty list of length <= rows*cols")
    if len(seq) % 2 != 0:
        raise NoGoCertificateError("Theorem 1.1 reachability with Black to move requires even alternating sequence (|B|=|W|)")

    cur = [0] * V
    for ply, v_raw in enumerate(seq):
        v = _parse_int(v_raw, f"play_sequence[{ply}]")
        if not (0 <= v < V):
            raise NoGoCertificateError(f"play_sequence[{ply}]={v} out of range 0..{V-1}")
        color = 1 if ply % 2 == 0 else 2
        if not is_legal_nogo_move(cur, adj, v, color):
            raise NoGoCertificateError(f"Illegal NoGo move at ply {ply} (vertex={v}, color={color})")
        cur[v] = color

    if tuple(cur) != target:
        raise NoGoCertificateError("Replayed play_sequence does not match target_board")

    b_moves = len(legal_nogo_moves(target, adj, 1))
    w_moves = len(legal_nogo_moves(target, adj, 2))
    if _parse_int(cert["claimed_black_moves"], "claimed_black_moves") != b_moves:
        raise NoGoCertificateError(f"claimed_black_moves mismatch: exact={b_moves}")
    if _parse_int(cert["claimed_white_moves"], "claimed_white_moves") != w_moves:
        raise NoGoCertificateError(f"claimed_white_moves mismatch: exact={w_moves}")

    return {
        "verified": True,
        "mode": cert["mode"],
        "grid": f"{rows}x{cols}",
        "plies_replayed": len(seq),
        "black_legal_moves": b_moves,
        "white_legal_moves": w_moves,
    }


def _verify_mode2_gadget_minimax(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema", "mode", "name", "rows", "cols", "ruleset", "to_move",
        "board", "claimed_winner", "claimed_winning_move",
    }
    if set(cert.keys()) != req:
        raise NoGoCertificateError(f"Mode 2 key mismatch: {sorted(set(cert.keys()) ^ req)}")
    rows = _parse_int(cert["rows"], "rows")
    cols = _parse_int(cert["cols"], "cols")
    if not (2 <= rows <= 6) or not (2 <= cols <= 6):
        raise NoGoCertificateError("Require 2 <= rows, cols <= 6 for exact minimax")
    ruleset = cert["ruleset"]
    if ruleset not in ("normal", "misere"):
        raise NoGoCertificateError(f"Invalid ruleset: {ruleset!r}")
    to_move = _parse_int(cert["to_move"], "to_move")
    if to_move not in (1, 2):
        raise NoGoCertificateError("to_move must be 1 (Black) or 2 (White)")

    V, adj = grid_graph(rows, cols)
    board = _parse_board(cert["board"], V, "board")
    if not is_legal_nogo_position(board, adj):
        raise NoGoCertificateError("Initial board is not a legal NoGo position")
    empty_cnt = board.count(0)
    if empty_cnt > 12:
        raise NoGoCertificateError("Cap empty vertices <= 12 for bounded exact minimax replay")

    winner, _, states = solve_nogo_minimax(board, adj, to_move, misere=(ruleset == "misere"))
    claimed_winner = _parse_int(cert["claimed_winner"], "claimed_winner")
    if claimed_winner != winner:
        raise NoGoCertificateError(f"claimed_winner mismatch: exact={winner}")

    wmv = cert["claimed_winning_move"]
    if winner == to_move:
        moves = legal_nogo_moves(board, adj, to_move)
        if not moves:
            # Misere immediate terminal win!
            if wmv is not None:
                raise NoGoCertificateError("Immediate terminal misere win requires claimed_winning_move=null")
        else:
            mv_i = _parse_int(wmv, "claimed_winning_move")
            if mv_i not in moves:
                raise NoGoCertificateError(f"claimed_winning_move={mv_i} is not legal")
            nxt = list(board)
            nxt[mv_i] = to_move
            opp = 2 if to_move == 1 else 1
            w_after, _, _ = solve_nogo_minimax(tuple(nxt), adj, opp, misere=(ruleset == "misere"))
            if w_after != to_move:
                raise NoGoCertificateError(f"claimed_winning_move={mv_i} does NOT preserve winning strategy")
    else:
        if wmv is not None:
            raise NoGoCertificateError("Losing player must have claimed_winning_move=null")

    return {
        "verified": True,
        "mode": cert["mode"],
        "ruleset": ruleset,
        "empty_cells": empty_cnt,
        "winner": winner,
        "states_evaluated": states,
    }


def _verify_mode3_coins_are_lava(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema", "mode", "name", "num_coins", "strings", "to_move",
        "claimed_winner", "claimed_winning_string_idx", "claimed_legal_cuts",
    }
    if set(cert.keys()) != req:
        raise NoGoCertificateError(f"Mode 3 key mismatch: {sorted(set(cert.keys()) ^ req)}")
    n = _parse_int(cert["num_coins"], "num_coins")
    if not (2 <= n <= 16):
        raise NoGoCertificateError("Require 2 <= num_coins <= 16")
    to_move = _parse_int(cert["to_move"], "to_move")
    if to_move not in (1, 2):
        raise NoGoCertificateError("to_move must be 1 or 2")
    raw_s = cert["strings"]
    if type(raw_s) is not list or not (1 <= len(raw_s) <= 18):
        raise NoGoCertificateError("Require 1 <= len(strings) <= 18")
    strings: List[Tuple[int, int]] = []
    deg = [0] * n
    for i, e in enumerate(raw_s):
        if type(e) is not list or len(e) != 2:
            raise NoGoCertificateError(f"strings[{i}] must be [u, v]")
        u, v = _parse_int(e[0], f"strings[{i}][0]"), _parse_int(e[1], f"strings[{i}][1]")
        if u == v or not (0 <= u < n) or not (0 <= v < n):
            raise NoGoCertificateError(f"strings[{i}] invalid endpoints ({u}, {v})")
        strings.append((u, v))
        deg[u] += 1
        deg[v] += 1
    if any(d == 0 for d in deg):
        raise NoGoCertificateError("Initial Coins-are-Lava board contains an isolated (dead) coin")

    legal_cuts = [i for i, (u, v) in enumerate(strings) if deg[u] >= 2 and deg[v] >= 2]
    if _parse_int(cert["claimed_legal_cuts"], "claimed_legal_cuts") != len(legal_cuts):
        raise NoGoCertificateError(f"claimed_legal_cuts mismatch: exact={len(legal_cuts)}")

    winner, _, states = solve_coins_are_lava_minimax(n, strings, to_move)
    if _parse_int(cert["claimed_winner"], "claimed_winner") != winner:
        raise NoGoCertificateError(f"claimed_winner mismatch: exact={winner}")

    w_idx = cert["claimed_winning_string_idx"]
    if winner == to_move:
        idx_i = _parse_int(w_idx, "claimed_winning_string_idx")
        if idx_i not in legal_cuts:
            raise NoGoCertificateError(f"claimed_winning_string_idx={idx_i} is not a legal cut")
        rem = [strings[k] for k in range(len(strings)) if k != idx_i]
        opp = 2 if to_move == 1 else 1
        w_after, _, _ = solve_coins_are_lava_minimax(n, rem, opp)
        if w_after != to_move:
            raise NoGoCertificateError(f"claimed_winning_string_idx={idx_i} is NOT a winning cut")
    else:
        if w_idx is not None:
            raise NoGoCertificateError("Losing player must have claimed_winning_string_idx=null")

    return {
        "verified": True,
        "mode": cert["mode"],
        "num_coins": n,
        "num_strings": len(strings),
        "winner": winner,
        "states_evaluated": states,
    }


def _verify_mode4_subcubic_bipartite(cert: Dict[str, Any]) -> Dict[str, Any]:
    req = {
        "schema", "mode", "name", "num_verts", "edges", "board", "to_move",
        "claimed_max_degree", "claimed_winner", "claimed_winning_move",
    }
    if set(cert.keys()) != req:
        raise NoGoCertificateError(f"Mode 4 key mismatch: {sorted(set(cert.keys()) ^ req)}")
    n = _parse_int(cert["num_verts"], "num_verts")
    if not (2 <= n <= 16):
        raise NoGoCertificateError("Require 2 <= num_verts <= 16")
    to_move = _parse_int(cert["to_move"], "to_move")
    if to_move not in (1, 2):
        raise NoGoCertificateError("to_move must be 1 or 2")
    raw_e = cert["edges"]
    if type(raw_e) is not list or len(raw_e) == 0:
        raise NoGoCertificateError("edges must be non-empty list")
    edges: List[Tuple[int, int]] = []
    for i, e in enumerate(raw_e):
        if type(e) is not list or len(e) != 2:
            raise NoGoCertificateError(f"edges[{i}] must be [u, v]")
        edges.append((_parse_int(e[0], f"edges[{i}][0]"), _parse_int(e[1], f"edges[{i}][1]")))

    ok_g, max_deg, _ = check_connected_bipartite_subcubic(n, edges)
    if not ok_g:
        raise NoGoCertificateError("Graph is not simple, connected, bipartite, and subcubic (Delta <= 3)")
    if _parse_int(cert["claimed_max_degree"], "claimed_max_degree") != max_deg:
        raise NoGoCertificateError(f"claimed_max_degree mismatch: exact={max_deg}")

    adj = graph_from_edges(n, edges)
    board = _parse_board(cert["board"], n, "board")
    if not is_legal_nogo_position(board, adj):
        raise NoGoCertificateError("Initial board is not a legal Graph NoGo position")
    if board.count(0) > 12:
        raise NoGoCertificateError("Cap empty vertices <= 12 for bounded exact minimax replay")

    winner, _, states = solve_nogo_minimax(board, adj, to_move, misere=False)
    if _parse_int(cert["claimed_winner"], "claimed_winner") != winner:
        raise NoGoCertificateError(f"claimed_winner mismatch: exact={winner}")

    wmv = cert["claimed_winning_move"]
    if winner == to_move:
        mv_i = _parse_int(wmv, "claimed_winning_move")
        moves = legal_nogo_moves(board, adj, to_move)
        if mv_i not in moves:
            raise NoGoCertificateError(f"claimed_winning_move={mv_i} is not legal")
        nxt = list(board)
        nxt[mv_i] = to_move
        opp = 2 if to_move == 1 else 1
        w_after, _, _ = solve_nogo_minimax(tuple(nxt), adj, opp, misere=False)
        if w_after != to_move:
            raise NoGoCertificateError(f"claimed_winning_move={mv_i} does NOT preserve winning strategy")
    else:
        if wmv is not None:
            raise NoGoCertificateError("Losing player must have claimed_winning_move=null")

    return {
        "verified": True,
        "mode": cert["mode"],
        "num_verts": n,
        "max_degree": max_deg,
        "winner": winner,
        "states_evaluated": states,
    }


def verify_nogo_certificate_exact(cert: Dict[str, Any]) -> Dict[str, Any]:
    if type(cert) is not dict:
        raise NoGoCertificateError("Certificate root must be a dict")
    _assert_strict_json_types(cert)
    if cert.get("schema") != SCHEMA_VERSION:
        raise NoGoCertificateError(f"Invalid schema: {cert.get('schema')!r}")
    name = cert.get("name")
    if type(name) is not str or not name.strip():
        raise NoGoCertificateError(f"Certificate name must be non-empty str, got {name!r}")
    mode = cert.get("mode")
    if mode == "nogo_board_legality_and_reachability":
        return _verify_mode1_reachability(cert)
    if mode == "b2cl_gadget_minimax_normal_misere":
        return _verify_mode2_gadget_minimax(cert)
    if mode == "coins_are_lava_exact_minimax":
        return _verify_mode3_coins_are_lava(cert)
    if mode == "subcubic_bipartite_graph_nogo":
        return _verify_mode4_subcubic_bipartite(cert)
    raise NoGoCertificateError(f"Unknown mode: {mode!r}")
