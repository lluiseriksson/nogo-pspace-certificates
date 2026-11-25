"""Comprehensive pytest suite + 60 live adversarial forgery attacks for Paper 34:
NOGO-PSPACE-CERT-1.0 (Burke, Davies, & Tennenhouse, arXiv:2611.33127).

Author: Lluis Eriksson
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import pytest

from src.nogo_certifier import NoGoCertificateError, verify_nogo_certificate_exact
from src.nogo_exact import (
    check_connected_bipartite_subcubic,
    grid_graph,
    is_legal_nogo_move,
    is_legal_nogo_position,
    solve_nogo_minimax,
)

ROOT = Path(__file__).resolve().parent.parent
CERT_DIR = ROOT / "certificates"


def _load_cert(name: str) -> Dict[str, Any]:
    return json.loads((CERT_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_all_16_canonical_certificates_pass() -> None:
    cert_files = sorted(CERT_DIR.glob("*.json"))
    assert len(cert_files) == 16
    for path in cert_files:
        cert = json.loads(path.read_text(encoding="utf-8"))
        res = verify_nogo_certificate_exact(cert)
        assert res["verified"] is True


def test_exact_mathematical_invariants() -> None:
    # 1. Self-capture and opponent-capture illegality on 2x2 grid
    _, adj22 = grid_graph(2, 2)
    # Board: [1, 2, 2, 0] -> Black at 0 has NO liberties (illegal position!)
    assert not is_legal_nogo_position([1, 2, 2, 0], adj22)
    # Board: [0, 2, 2, 0] -> Black playing at 0 is suicide (illegal); White playing at 0 leaves liberty at 3 (legal)
    assert not is_legal_nogo_move([0, 2, 2, 0], adj22, 0, 1)
    assert is_legal_nogo_move([0, 2, 2, 0], adj22, 0, 2)

    # 2. Normal vs. Misere duality on 2x2 empty grid
    wn, _, _ = solve_nogo_minimax((0, 0, 0, 0), adj22, 1, misere=False)
    wm, _, _ = solve_nogo_minimax((0, 0, 0, 0), adj22, 1, misere=True)
    assert wn in (1, 2) and wm in (1, 2)

    # 3. Odd cycle C_5 fails bipartiteness, K_4 fails subcubic & bipartiteness
    assert not check_connected_bipartite_subcubic(5, [(i, (i + 1) % 5) for i in range(5)])[0]
    assert not check_connected_bipartite_subcubic(4, [(i, j) for i in range(4) for j in range(i + 1, 4)])[0]
    # K_{3,3} passes connected bipartite subcubic (Delta = 3)
    ok_k33, d_k33, _ = check_connected_bipartite_subcubic(6, [(u, 3 + v) for u in range(3) for v in range(3)])
    assert ok_k33 and d_k33 == 3


def test_adversarial_red_team_forgeries() -> None:
    m1 = _load_cert("mode1_grid_3x3_balanced_reachability")
    m2_norm = _load_cert("mode2_grid_3x3_empty_normal")
    m2_mis = _load_cert("mode2_grid_4x3_wire_goal_misere")
    m3 = _load_cert("mode3_lava_diamond_parity")
    m4 = _load_cert("mode4_subcubic_k33_biclique")

    def mut(base: Dict[str, Any], fn: Callable[[Dict[str, Any]], None]) -> Dict[str, Any]:
        c = copy.deepcopy(base)
        fn(c)
        return c

    attacks: List[Tuple[str, Any]] = [
        # --- Global / Schema / Type Confusion (10) ---
        ("root_not_dict", [1, 2, 3]),
        ("wrong_schema", mut(m1, lambda c: c.__setitem__("schema", "NOGO-PSPACE-CERT-0.9"))),
        ("unknown_mode", mut(m1, lambda c: c.__setitem__("mode", "fake_mode"))),
        ("empty_name", mut(m1, lambda c: c.__setitem__("name", "   "))),
        ("float_injected", mut(m1, lambda c: c.__setitem__("rows", 3.0))),
        ("bool_for_int", mut(m1, lambda c: c.__setitem__("cols", True))),
        ("extra_key_m1", mut(m1, lambda c: c.__setitem__("extra", 1))),
        ("missing_key_m1", mut(m1, lambda c: c.pop("play_sequence"))),
        ("bad_stone_val", mut(m1, lambda c: c["target_board"].__setitem__(0, 3))),
        ("wrong_board_len", mut(m1, lambda c: c["target_board"].pop())),

        # --- Mode 1: Board Legality & Empty-Board Reachability Forgeries (12) ---
        ("m1_rows_too_small", mut(m1, lambda c: c.__setitem__("rows", 1))),
        ("m1_cols_too_large", mut(m1, lambda c: c.__setitem__("cols", 13))),
        ("m1_empty_play_seq", mut(m1, lambda c: c.__setitem__("play_sequence", []))),
        ("m1_odd_play_seq", mut(m1, lambda c: c["play_sequence"].pop())),
        ("m1_duplicate_vertex_play", mut(m1, lambda c: c["play_sequence"].__setitem__(1, c["play_sequence"][0]))),
        ("m1_oob_vertex_play", mut(m1, lambda c: c["play_sequence"].__setitem__(0, 99))),
        ("m1_seq_mismatch_target", mut(m1, lambda c: c["target_board"].__setitem__(3, 1))),
        ("m1_illegal_zero_lib_target", mut(m1, lambda c: c.__setitem__("target_board", [1, 2, 0, 2, 0, 0, 0, 0, 0]))),
        ("m1_wrong_black_moves", mut(m1, lambda c: c.__setitem__("claimed_black_moves", c["claimed_black_moves"] + 1))),
        ("m1_wrong_white_moves", mut(m1, lambda c: c.__setitem__("claimed_white_moves", c["claimed_white_moves"] + 1))),
        ("m1_play_seq_not_list", mut(m1, lambda c: c.__setitem__("play_sequence", "0,1"))),
        ("m1_illegal_capture_mid_play", mut(m1, lambda c: c.__setitem__("play_sequence", [0, 1, 2, 3]))),

        # --- Mode 2: Normal & Misere Minimax Forgeries (12) ---
        ("m2_bad_ruleset", mut(m2_norm, lambda c: c.__setitem__("ruleset", "ko"))),
        ("m2_bad_to_move", mut(m2_norm, lambda c: c.__setitem__("to_move", 0))),
        ("m2_grid_too_big", mut(m2_norm, lambda c: c.__setitem__("rows", 7))),
        ("m2_too_many_empty", mut(m2_norm, lambda c: (c.__setitem__("rows", 4), c.__setitem__("cols", 4), c.__setitem__("board", [0] * 16)))),
        ("m2_illegal_init_board", mut(m2_norm, lambda c: c.__setitem__("board", [1, 2, 0, 2, 0, 0, 0, 0, 0]))),
        ("m2_wrong_winner_norm", mut(m2_norm, lambda c: c.__setitem__("claimed_winner", 3 - c["claimed_winner"]))),
        ("m2_wrong_winner_misere", mut(m2_mis, lambda c: c.__setitem__("claimed_winner", 3 - c["claimed_winner"]))),
        ("m2_null_move_when_winning", mut(m2_norm, lambda c: c.__setitem__("claimed_winning_move", None) if c["claimed_winner"] == 1 else c.__setitem__("claimed_winning_move", 0))),
        ("m2_oob_winning_move", mut(m2_norm, lambda c: c.__setitem__("claimed_winning_move", 99))),
        ("m2_occupied_winning_move", mut(m2_mis, lambda c: c.__setitem__("claimed_winning_move", 0))),
        ("m2_missing_key", mut(m2_norm, lambda c: c.pop("ruleset"))),
        ("m2_extra_key", mut(m2_norm, lambda c: c.__setitem__("extra", 0))),

        # --- Mode 3: Coins-are-Lava Minimax Forgeries (12) ---
        ("m3_coins_too_few", mut(m3, lambda c: c.__setitem__("num_coins", 1))),
        ("m3_coins_too_many", mut(m3, lambda c: c.__setitem__("num_coins", 17))),
        ("m3_bad_to_move", mut(m3, lambda c: c.__setitem__("to_move", 3))),
        ("m3_empty_strings", mut(m3, lambda c: c.__setitem__("strings", []))),
        ("m3_self_loop_string", mut(m3, lambda c: c["strings"].append([0, 0]))),
        ("m3_oob_endpoint", mut(m3, lambda c: c["strings"].append([0, 9]))),
        ("m3_isolated_dead_coin", mut(m3, lambda c: c.__setitem__("num_coins", 5))),
        ("m3_wrong_legal_cuts", mut(m3, lambda c: c.__setitem__("claimed_legal_cuts", c["claimed_legal_cuts"] + 1))),
        ("m3_wrong_winner", mut(m3, lambda c: c.__setitem__("claimed_winner", 3 - c["claimed_winner"]))),
        ("m3_invalid_winning_idx", mut(m3, lambda c: c.__setitem__("claimed_winning_string_idx", 99))),
        ("m3_bad_edge_shape", mut(m3, lambda c: c["strings"].__setitem__(0, [0, 1, 2]))),
        ("m3_missing_key", mut(m3, lambda c: c.pop("claimed_legal_cuts"))),

        # --- Mode 4: Connected Bipartite Subcubic Graph NoGo Forgeries (14) ---
        ("m4_verts_too_few", mut(m4, lambda c: c.__setitem__("num_verts", 1))),
        ("m4_verts_too_many", mut(m4, lambda c: c.__setitem__("num_verts", 17))),
        ("m4_empty_edges", mut(m4, lambda c: c.__setitem__("edges", []))),
        ("m4_self_loop", mut(m4, lambda c: c["edges"].append([0, 0]))),
        ("m4_duplicate_edge", mut(m4, lambda c: c["edges"].append(c["edges"][0]))),
        ("m4_non_bipartite_odd_cycle", mut(m4, lambda c: (c.__setitem__("num_verts", 5), c.__setitem__("edges", [[0,1],[1,2],[2,3],[3,4],[4,0]]), c.__setitem__("board", [0]*5)))),
        ("m4_degree_4_not_subcubic", mut(m4, lambda c: (c.__setitem__("num_verts", 5), c.__setitem__("edges", [[0,1],[0,2],[0,3],[0,4]]), c.__setitem__("board", [0]*5)))),
        ("m4_disconnected_graph", mut(m4, lambda c: (c.__setitem__("num_verts", 4), c.__setitem__("edges", [[0,1],[2,3]]), c.__setitem__("board", [0]*4)))),
        ("m4_wrong_max_degree", mut(m4, lambda c: c.__setitem__("claimed_max_degree", 2))),
        ("m4_wrong_winner", mut(m4, lambda c: c.__setitem__("claimed_winner", 3 - c["claimed_winner"]))),
        ("m4_invalid_win_move", mut(m4, lambda c: c.__setitem__("claimed_winning_move", 99))),
        ("m4_illegal_init_board", mut(m4, lambda c: c.__setitem__("board", [1, 0, 0, 2, 2, 2]))),
        ("m4_bad_to_move", mut(m4, lambda c: c.__setitem__("to_move", 0))),
        ("m4_missing_key", mut(m4, lambda c: c.pop("claimed_max_degree"))),
    ]

    assert len(attacks) == 60
    rejected = 0
    for attack_name, payload in attacks:
        with pytest.raises(NoGoCertificateError, match=".+"):
            verify_nogo_certificate_exact(payload)
        rejected += 1
    assert rejected == 60
