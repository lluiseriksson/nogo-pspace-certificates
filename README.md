# Machine-Checked Exact-Integer Certificates for Normal and Misère Grid NoGo, Coins-are-Lava, and Subcubic Bipartite Graph NoGo PSPACE-Completeness

**Author:** Lluis Eriksson (prepared with transparent AI assistance via Google Antigravity)
**Target Reference:** Kyle Burke, Alfie Davies, & Craig Tennenhouse, *Winning and losing NoGo is PSPACE-complete*, `arXiv:2611.33127` (November 24, 2026).
**Licenses:** Manuscript (`paper/main.tex`, `paper/main.pdf`) under `CC-BY-4.0`; code, Lean 4 proofs, and exact certificates under `MIT`.

## Highlights
- **Zero-Dependency Lean 4 Kernel (`lean/NoGoPSPACE.lean`, Lean 4.35.0):** 18 constructive theorems, `0` `sorry`, `0` warnings, `0` `Classical.choice`, `0` `Lean.ofReduceBool`, **9 zero-axiom theorems** (`none`).
- **Pure-Stdlib Zero-Float Game-Tree Verifier (`NOGO-PSPACE-CERT-1.0`, `src/nogo_certifier.py`):** Four exact modes auditing $n \times n$ grid legality and ply-by-ply empty-board reachability, exact normal and misère grid NoGo minimax, exact `Coins-are-Lava` minimax, and connected bipartite subcubic ($\Delta \le 3$) Graph NoGo minimax.
- **Canonical Atlas & Adversarial Audit:** 16/16 canonical certificates replayed in `0.060–6.495 ms`, exact normal-vs.-misère winner flips across grids ($2\times 2, 2\times 4$) and subcubic bipartite graphs ($K_{3,3}, Q_3, L_8$), and **60/60 live adversarial forgery attacks rejected**.

## Quick Reproduction
```bash
# 1. Build & audit Lean 4 kernel
cd lean && lake build && lake env lean AuditAxioms.lean && cd ..

# 2. Run deterministic end-to-end verification (Lean + 16 certs + 60/60 attacks + SHA-256 manifest)
python scripts/verify_all.py

# Optional: regenerate certificates, wall-clock benchmark JSONs, and figures
python scripts/run_all_experiments.py
python scripts/make_figures.py
```
