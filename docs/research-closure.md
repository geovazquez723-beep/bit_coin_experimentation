# HASHLAB research closure note

2026-10-16. Research Director decision: **NO-GO on modified Bitcoin mining.** E002 development, G1 qualification, Q-2 planning, cloud provisioning and further research execution are stopped. This note records what was and was not established. **The hypothesis has not been mathematically disproved**; it was tested at one modest scale, found consistent with the null, and judged economically unviable.

## 1. Original hypothesis
Whether a structurally different candidate-selection process (sequential, patterned, structured or sampled candidates) changes the probability that SHA-256 output falls below a proof-of-work-style target, relative to uniform selection. For real mining the question is whether any selection rule raises the success probability **per SHA256d evaluation** of an 80-byte header enough to pay for its own cost. The working assumption (null) is that SHA-256 outputs behave as uniform pseudorandom values for distinct inputs.

## 2. Experiment 001 (executed, sealed)
Run `20261011T205056Z-exp001-fc1d75fc` (11 sealed files, source `ef595f5`): 10 generators (sequential, uniform, patterned, structured, random bytes; 8- and 16-byte domains), **single SHA-256**, 8-bit leading-zero target (p₀ = 1/256), 500,000 attempts per phase per generator.
Result: all 10 classified **consistent with the null**; no corrected discovery signal; no replicated signal. Typical 99% rate-ratio interval ≈ ±7% (e.g. seq-be-w8 validation 1.012, CI 0.955–1.072). This does **not** establish equivalence and cannot exclude effects below roughly 7%, nor says anything about the deep tail relevant to real difficulty or about SHA256d.
Reproduction: the 86 secondary floating-point differences found on re-analysis under CPython 3.12/3.13 are caused by CPython 3.12's compensated `sum()`; CPython 3.11.0 reproduces the sealed analysis bit for bit; no decision changes (Reviews 036–038, `e002-g1-historical-platform-closure.md`).

## 3. Experiment 002 (designed, built, **not executed**)
Pre-registered protocol (Revision 9; `docs/proposals/experiment-002-research-design.md`): hypothesis H_S, a ≥ 2% relative lift for at least one of three arms (A1 exact Algorithm D selection, A2 header-shaped 76-byte-prefix + nonce clusters, A3 Hamming-weight rank sampling), with null/positive controls, 180.2 M producer evaluations and an independent full audit.
State: production-disabled kernel, independent verifier and independent SHA-256 backend implemented and bounded-qualified (G1-A…G1-D; 2,000 tests passing at the last full run, 11 skipped locally, the 11 real-symlink tests passing on a separate hosted Windows host). **No E002 seed was selected, no QA2 run, no production execution, no confirmatory data exists.** G1 was never accepted; Q-2 (independent second-host replay) was never run. No scientific claim follows from E002.

## 4. Applicability to real Bitcoin mining
* Real validity is SHA256d(header) < target; the experiments used single SHA-256 at an easy threshold. An effect at 8 bits has no demonstrated relation to a tail of ~10⁻²³–10⁻²⁴ nor to the second hash, which re-randomises its 32-byte input.
* Only A2/N2 are 80-byte header-shaped, with random prefixes. Real headers leave only merkle root (extranonce), time and nonce free; a full 2³² nonce sweep is exhaustive in any order, so reordering cannot change expected hits — only skipping nonces could, which requires an unidentified higher-density subset.
* Nothing in the repository shows such a subset; nothing proves none exists.

## 5. Measured candidate-selection cost (Python, bounded probes, G1-B; early-stream only)
SHA-256 per candidate 0.4–0.6 µs; exact Algorithm D ≈ 105 µs per candidate (early stream; later behaviour projected, not measured); A3 ≈ 2–10 µs; N1/P/N2 ≈ 4–8 µs; whole producer ≈ 58 µs per evaluation (≈ 100× the hash). A selector with lift δ pays off only if its cost per candidate is below δ of one hash; for a 2% lift that is far below anything measured, and conventional nonce iteration is essentially free.

## 6. Economic conclusion (supplied assumptions: $100,000/BTC, 3.125 BTC subsidy, difficulty 1.2×10¹⁴, $0.15/kWh; not verified, order-of-magnitude)
Expected revenue ≈ 6.1×10⁻¹⁹ $/hash. A CPU at 10⁸ H/s and 100 W costs ≈ 4.2×10⁻¹⁴ $/hash in electricity: **≈ 68,700× revenue** (corrects the 60× in the preliminary assessment, which used a wrong unit conversion). Even an ASIC at 20 J/TH costs ≈ 8.3×10⁻¹⁹ $/hash, **≈ 1.4× revenue** under the same assumptions (the preliminary note's "700× margin" was also wrong). The sign is unfavourable before any selection overhead; a selection layer cannot rescue it. Hardware-level viability would additionally require the rule to be free in silicon.

## 7. Remaining scientific uncertainty
Effects below ≈ 7% at 8 bits (E001 power); any behaviour at deep thresholds or under SHA256d; header-structured inputs; structural classes not tested. The proposed 10¹⁰-hash proof of concept was judged underpowered (it could detect ≈ 10% at best) and is **not** to be run. E002 would have been the powered test of 2% effects and remains unexecuted.

## 8. State preserved
All code, accepted evidence (sealed E001, retained S1.4 audit, G1 handoffs and data), experiments and findings are preserved in the repository and history; nothing was deleted or rewritten. Merged on `main` through PR #10 (`d42cfa8`). Open: PR #11 (removes only the unintended Q-1 workflow; diff verified single file). Unmerged and uncommitted: this note and `docs/reviews/e002-g1-q2-second-host-runbook.md` (a prepared, never-executed Q-2 procedure). No further spending, development or execution is authorized.
