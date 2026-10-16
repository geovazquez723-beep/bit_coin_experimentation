"""Transparent E002 G1-B resource model built from the retained bounded probe results.

    python tools/model_e002_g1b_resources.py RESULTS_DIR [--markdown OUT.md] [--json OUT.json]

Every stage is labelled:
  M  rate measured by a bounded probe (representativeness caveats in the handoff)
  D  derived arithmetically from measured components
  A  assumption (no direct measurement); carries the widest range
Ranges are low = measured value, central = x1.25, high = x2.5 for CPU stages (bounded runs of <=10^4 events
cannot show sustained-run effects); assumptions use x0.5 / x1 / x3. Nothing here is a measured full-workload runtime.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'src')]

COUNTS = dict(A1=30_000_000, A2=30_000_000, A3=30_000_000, N1=30_000_000, N2=30_000_000, P1=200_000,
              P2p=15_000_000, P2m=15_000_000)
EVALUATIONS = sum(COUNTS.values())
BLOCKS = 240_200_000
A3_RANKS_SCANNED = 82_128_984
HISTORY_OCCURRENCES = 7_000_000
CPU_FACTORS = (1.0, 1.25, 2.5)
ASSUMED_FACTORS = (0.5, 1.0, 3.0)


def load(directory):
    out = {}
    for path in Path(directory).glob('*.json'):
        record = json.loads(path.read_text(encoding='utf-8'))
        if 'probe' in record and 'result' in record:
            out[record['probe']] = record['result']
    return out


def stage(name, group, seconds, label, factors=None, note=''):
    f = factors or (CPU_FACTORS if label in ('M', 'D') else ASSUMED_FACTORS)
    return dict(stage=name, group=group, label=label, seconds=[seconds * x for x in f], note=note)


def model(r):
    a1p = r['a1-producer-10k']['microseconds_per_output']['mean']
    a1v = r['a1-verifier-10k']['microseconds_per_output']['mean']
    late_p = r['a1-late-producer']['states'][0]['microseconds_per_output']['mean']   # n=30,000 state; n<=300 states are <0.001% of outputs
    late_v = r['a1-late-verifier']['states'][0]['microseconds_per_output']['mean']
    a3, ctl, ser, hp, hv, disk = r['a3'], r['controls'], r['serialize'], r['hash-producer'], r['hash-verifier'], r['disk-io']
    us = 1e-6
    ratio = A3_RANKS_SCANNED / COUNTS['A3']
    stages = []
    # ---- producer ---------------------------------------------------------------------------------------
    stages += [
        stage('A1 Algorithm D (30M ranks)', 'producer-generation', COUNTS['A1'] * max(a1p, late_p) * us, 'M',
              note='max of early-stream mean and synthetic late-state means; 4 compares, 2 random blocks/output'),
        stage('A2 prefix+nonce stream', 'producer-generation', COUNTS['A2'] * 6.0 * us, 'A',
              note='not individually probed; bounded by Attempt construction (4.5 us) + concatenation'),
        stage('A3 Algorithm S scan + unrank + encode', 'producer-generation',
              COUNTS['A3'] * (a3['producer_scan']['microseconds_per_emitted'] * 1 + a3['SYNTHETIC_unrank_evenly_spaced_across_population_us']
                              + a3['encode_to_bytes_us']) * us, 'D',
              note='scan 1.7 us/emitted (early) + unrank at weight-6 mix 5.0 us; scan scales with ranks scanned (x%.2f)' % ratio),
        stage('N1 forward + rejection checks', 'producer-generation', COUNTS['N1'] * ctl['producer_n1_provider_us_per_attempt'] * us, 'M',
              note='real provider incl. row dict; history set was 100k inversions, not 6.0M'),
        stage('P1/P2+/P2- forward + checks', 'producer-generation',
              (COUNTS['P1'] + COUNTS['P2p'] + COUNTS['P2m']) * ctl['producer_p_provider_us_per_attempt'] * us, 'M'),
        stage('N2 80-byte stream + A2 membership', 'producer-generation', COUNTS['N2'] * ctl['producer_n2_provider_us_per_attempt'] * us, 'M'),
    ]
    per_attempt_overhead = (a3['attempt_construction_us'] + ser['accumulator_add_us_incl_record_validation']
                            + ser['control_transform_seconds'] / 9901 * 1e6 + 2.0)   # + eligibility base ~2.0 (A)
    elig = dict(A1=1.5, A2=3.0, A3=a3['kernel_eligibility_rank_check_us'],
                N1=ctl['producer_feistel_forward_n1_us'] + ctl['producer_structural_rejection_check_us'] + ctl['inverse_index_membership_100k_set_us'],
                N2=1.0)
    elig['P'] = elig['N1']
    elig_seconds = sum(COUNTS[k] * elig[k] for k in ('A1', 'A2', 'A3', 'N1', 'N2')) * us + (
        COUNTS['P1'] + COUNTS['P2p'] + COUNTS['P2m']) * elig['P'] * us
    stages += [
        stage('Kernel eligibility re-check (second Feistel/rank per control/A3)', 'producer-accounting', elig_seconds, 'D'),
        stage('Attempt construction + Accumulator.add + ControlEngine.transform', 'producer-accounting',
              EVALUATIONS * (per_attempt_overhead - 2.0) * us, 'M'),
        stage('SHA-256 evaluation (OpenSSL, 180.2M evals)', 'producer-hash', EVALUATIONS * hp['microseconds_per_evaluation'] * us, 'M',
              note='%.0f ns/eval; hashing is not a bottleneck' % (1000 * hp['microseconds_per_evaluation'])),
        stage('Row serialization (encode_row)', 'producer-serialization', EVALUATIONS * ser['encode_row_us'] * us, 'M'),
    ]
    chunks = -(-EVALUATIONS // 4096)
    io_low = chunks * disk['ms_per_file_create_write_fsync'] / 1000
    io_high = chunks * 0.0138                # ChunkWriter in-situ: 41 ms for 3 chunks incl. encode, fsync, inventory re-read
    stages.append(dict(stage='Durable chunk writes + fsync + per-chunk inventory (%d files)' % chunks, group='producer-disk', label='M',
                       seconds=[io_low, (io_low + io_high) / 2, io_high * 1.5],
                       note='disk probe %.2f ms/file vs ChunkWriter in-situ ~13.8 ms/chunk; Defender real-time on; page-cache effects' % disk['ms_per_file_create_write_fsync']))
    inv = ctl['producer_feistel_inverse_us']
    stages.append(stage('History load: 7.0M occurrences inverted into index', 'producer-setup', HISTORY_OCCURRENCES * (inv + 0.2) * us, 'D',
                        note='consistent with the 55 s bounded producer runs (dominated by this load)'))
    stages.append(stage('Producer-side capture replay / authentication (iter_chunks)', 'producer-finalization',
                        chunks * ser['producer_iter_chunks_us_per_chunk_incl_decode'] * us, 'M'))
    # ---- verifier ---------------------------------------------------------------------------------------
    gos = a3['verifier_scan']['microseconds_per_emitted']
    vstages = [
        stage('A1 regeneration (interval arithmetic)', 'verifier-generation', COUNTS['A1'] * max(a1v, late_v) * us, 'M'),
        stage('A2 regeneration', 'verifier-generation', COUNTS['A2'] * 1.0 * us, 'A'),
        stage('A3 Algorithm S + Gosper', 'verifier-generation', COUNTS['A3'] * gos * us, 'M'),
        stage('N1/P Feistel + masks', 'verifier-generation',
              (COUNTS['N1'] + COUNTS['P1'] + COUNTS['P2p'] + COUNTS['P2m']) * (ctl['verifier_feistel_forward_us'] + ctl['verifier_structural_mask_us'] + 0.1) * us, 'M'),
        stage('N2 regeneration', 'verifier-generation', COUNTS['N2'] * (ctl['verifier_n2_stream_us'] + 0.1) * us, 'M'),
        stage('Independent SHA-256 rehash (HACL*)', 'verifier-hash', EVALUATIONS * ser['independent_rehash_us_per_candidate'] * us, 'M'),
        stage('Row pack/compare + transform + tally', 'verifier-compare', EVALUATIONS * 3.0 * us, 'A',
              note='earlier handoff measured 1.15 us/row for comparison alone; tally and transform added'),
        stage('History load (inverse index, 7.0M)', 'verifier-setup', HISTORY_OCCURRENCES * (ctl['verifier_feistel_inverse_us'] + 0.2) * us, 'D'),
    ]
    total_bytes = 25_944_000_000
    read_mbps = disk['sequential_read_mb_per_s']        # disk-io probe; the serialize probe's figure is page-cache hot
    read_hash = total_bytes / (read_mbps * 1e6)
    vstages.append(stage('Sequential read of 25.9 GB (NVMe C:, %.0f MB/s)' % read_mbps, 'verifier-disk', read_hash, 'M',
                         note='rate measured on just-written files; external USB HDD unmeasured; SHA-256 of chunks at 1.6 GB/s adds ~16 s'))
    archive = [
        stage('Manifest/inventory re-read of 43,995 chunk files', 'finalization', total_bytes / (read_mbps * 1e6), 'D'),
        stage('Copy to two off-machine copies (assumed 150 MB/s each)', 'finalization', 2 * total_bytes / 150e6, 'A', factors=(0.5, 1.0, 6.0),
              note='target media/network not specified; throughput is an assumption'),
        stage('Re-hash both copies (assumed 150 MB/s)', 'finalization', 2 * total_bytes / 150e6, 'A', factors=(0.5, 1.0, 6.0)),
        stage('Restored-copy verification pass (second full audit read)', 'finalization', read_hash, 'D',
              note='read cost only; the regeneration cost is the verifier table'),
    ]
    return stages, vstages, archive


def total(stages):
    return [sum(s['seconds'][i] for s in stages) for i in range(3)]


def hms(seconds):
    return '%d:%02d:%02d' % (seconds // 3600, seconds % 3600 // 60, seconds % 60)


def markdown(stages, vstages, archive):
    lines = []
    for title, rows in (('Producer', stages), ('Independent verifier (full audit)', vstages), ('Finalization and archival (mostly unmeasured)', archive)):
        lines += ['', '### ' + title, '', '| Stage | Basis | Low | Central | High | Note |', '|---|---|---|---|---|---|']
        for s in rows:
            lines.append('| %s | %s | %s | %s | %s | %s |' % ((s['stage'], s['label']) + tuple(hms(x) for x in s['seconds']) + (s['note'],)))
        t = total(rows)
        lines.append('| **Total (single-threaded sum)** | | **%s** | **%s** | **%s** | |' % tuple(hms(x) for x in t))
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    parser.add_argument('--markdown', type=Path)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    stages, vstages, archive = model(load(args.results))
    text = markdown(stages, vstages, archive)
    print(text)
    if args.markdown:
        args.markdown.write_text(text + '\n', encoding='utf-8')
    if args.json:
        args.json.write_text(json.dumps(dict(counts=COUNTS, producer=stages, verifier=vstages, archive=archive, producer_total=total(stages),
                                            verifier_total=total(vstages)), indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
