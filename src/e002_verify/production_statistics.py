"""Independent check of persisted measured production statistics. No HASHLAB imports.

Reuses the accepted independent primary/control/secondary reference calculations
(exact-law tails, Clopper-Pearson inversion, Holm, cluster/hull and secondary
chi-square families) against an independently validated, complete accounting.
The public report contains no counts, p-values or classifications. Floating
comparisons use the tolerances already accepted in ``integration_statistics``.
"""
from hashlib import sha256

from . import integration_statistics as stats
from .production_evidence import read_json_bytes, _require
from .production import FROZEN

SCHEMA = 'hashlab-e002-measured-statistics-v1'
REPORT = 'hashlab-e002-statistics-verification-v1'


def check_accounting(accounting):
    """Independent structural validation of a complete production accounting."""
    quotas = FROZEN.quotas()
    _require(type(accounting) is dict and set(accounting) == {'schema', 'secondary_identity', 'complete', 'streams'}
             and accounting['schema'] == 'hashlab-exp002-accounting-v2'
             and accounting['secondary_identity'] == 'hashlab-exp002-secondary-statistics-proposal-v2'
             and accounting['complete'] is True and type(accounting['streams']) is list
             and len(accounting['streams']) == len(quotas), 'complete frozen accounting required')
    for row, ((arm, stage), n) in zip(accounting['streams'], quotas.items()):
        _require((row['arm'], row['stage']) == (arm, stage) and row['trials'] == n
                 and type(row['successes']) is int and 0 <= row['successes'] <= n, 'stream geometry ' + arm + stage)
        for key, size in (('first_byte', 256), ('last_byte', 256), ('leading_zero_bits', 257)):
            _require(len(row[key]) == size and sum(row[key]) == n and all(type(x) is int and x >= 0 for x in row[key]),
                     'diagnostic totals')
        _require(row['first_byte'][0] == row['successes'] and sum(row['leading_zero_bits'][8:]) == row['successes'],
                 'target/diagnostic consistency')
        if arm in ('A2', 'N2'):
            _require(row['cluster_trials'] == [10000] * 1500 and sum(row['cluster_successes']) == row['successes']
                     and all(0 <= x <= 10000 for x in row['cluster_successes']), 'cluster accounting')
        if arm == 'A3':
            _require(sum(row['weight_trials']) == n and sum(row['weight_successes']) == row['successes'], 'weights')


def verify_measured(accounting, result):
    check_accounting(accounting)
    _require(type(result) is dict and set(result) == {'primary', 'controls', 'secondary'}, 'result families')
    rows = {(r['arm'], r['stage']): r for r in accounting['streams']}
    stats.family(rows, ['A1', 'A2', 'A3'], result['primary'], True)
    controls = result['controls']
    _require(set(controls) == {'statistical_gate_passed', 'nulls', 'positives'}, 'controls shape')
    stats.family(rows, ['N1', 'N2'], controls['nulls'], False)
    _require(len(controls['positives']) == 3, 'positive family shape')
    for arm, out, direction in zip(('P1', 'P2+', 'P2-'), controls['positives'], ('greater', 'greater', 'less')):
        k, n = rows[arm, 'C']['successes'], rows[arm, 'C']['trials']
        p = stats.binomial(k, n, direction)
        margin = stats.cp_check(out['interval'], k, n)
        _require(set(out) == {'p', 'detected', 'interval', 'margin', 'ratio'}
                 and stats._exact(out['detected'], p < stats.Decimal('.001')) and out['margin'] == margin
                 and stats._exact(out['ratio'], stats.rational(stats.Fraction(k * 256, n))), 'positive inference')
        stats.reported_number(out['p'], p)
    pos = controls['positives']
    passed = (pos[0]['detected'] and any(p['detected'] for p in pos[1:]) and all(p['margin'] != 'WITHIN' for p in pos[1:])
              and all(n['difference'] != 'REP' for n in controls['nulls']))
    _require(stats._exact(controls['statistical_gate_passed'], passed), 'control gate')
    stats.secondary(rows, result['secondary'])


def verify_statistics(statistics_bytes, accounting_bytes):
    """Public report; numeric results stay in the private statistics file."""
    document = read_json_bytes(statistics_bytes)
    accounting = read_json_bytes(accounting_bytes)
    _require(type(document) is dict and set(document) == {'schema', 'scope', 'accounting_sha256', 'plan_sha256', 'completion_sha256',
                                       'publication', 'result'}
             and document['publication'] == 'not-authorized'
             and document['schema'] == SCHEMA and document['scope'] == 'measured-production'
             and document['accounting_sha256'] == sha256(accounting_bytes).hexdigest(), 'statistics binding')
    verify_measured(accounting, document['result'])
    return dict(schema=REPORT, scope='measured-production', verification='independent-reference-recalculation',
                bindings=dict(accounting_sha256=document['accounting_sha256'], plan_sha256=document['plan_sha256'],
                              completion_sha256=document['completion_sha256'],
                              statistics_sha256=sha256(statistics_bytes).hexdigest()),
                claims=dict(numeric_results_disclosed=False, disclosure_authorized=False, execution_authorized=False))
