"""Paper 1: saved 800 m indicators -> selection, cosine and fixed examples.

The candidate definition is a scientific input. Expected results are read only
AFTER calculation, and cannot affect selection, fitting, or ranking.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.preprocessing import RobustScaler

FEATURES = ['road_density_Dl_m_per_ha', 'avg_circuity_A', 'degree_centrality_mean',
            'closeness_centrality_mean', 'basic_streets_per_node_avg',
            'basic_circuity_avg', 'basic_self_loop_proportion',
            'basic_clean_intersection_density_km']
ATOL = RTOL = 1e-12


def table(path):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def eligible(frame, quality, columns):
    if not frame.index.is_unique or not quality.index.is_unique:
        raise ValueError('duplicate station ID')
    if not set(frame.index) <= set(quality.index):
        raise ValueError('indicator IDs outside quality ledger')
    ids = quality.index[(quality.status == 'ok') & (quality.quality_hold == '')]
    if not set(ids) <= set(frame.index):
        raise ValueError('eligible station has no indicator row')
    values = frame.loc[ids, columns]
    if np.isinf(values.to_numpy()).any():
        raise ValueError('infinite indicator')
    return sorted(values.index[values.notna().all(axis=1)].tolist())


def select_features(frame):
    x = frame.to_numpy(dtype=float)
    if len(x) < 2 or not np.isfinite(x).all():
        raise ValueError('selection requires at least two finite rows')
    q25, q75 = np.percentile(x, [25, 75], axis=0, method='linear')
    iqr = q75 - q25
    lower, upper = q25 - 3 * iqr, q75 + 3 * iqr
    clipped = np.clip(x, lower, upper)
    scaler = RobustScaler().fit(clipped)
    z = pd.DataFrame(scaler.transform(clipped), columns=frame.columns)
    variance = z.var(ddof=1)
    pool = [f for f in frame if variance[f] > .05]
    corr = z[pool].corr().abs()
    if not pool or not np.isfinite(corr.to_numpy()).all():
        raise ValueError('empty or undefined selection')
    pairs = [{'a': a, 'b': b, 'abs_r': float(corr.loc[a, b])}
             for i, a in enumerate(pool) for b in pool[i + 1:]]
    selected, steps = [], []
    while pool:
        best = max(pool, key=lambda f: variance[f])  # first in candidate order on ties
        removed = [f for f in pool if f != best and corr.loc[best, f] > .7]
        pool = [f for f in pool if f != best and f not in removed]
        selected.append(best)
        steps.append({'step': len(selected), 'selected_feature': best,
                      'variance': float(variance[best]), 'removed_features': removed,
                      'removed_abs_correlations': [float(corr.loc[best, f]) for f in removed],
                      'remaining_count': len(pool)})
    prep = []
    for j, f in enumerate(frame):
        prep.append({'feature': f, 'n': len(x), 'raw_q25': q25[j], 'raw_q75': q75[j],
                     'raw_iqr': iqr[j], 'clip_lower': lower[j], 'clip_upper': upper[j],
                     'clip_low_count': int((x[:, j] < lower[j]).sum()),
                     'clip_high_count': int((x[:, j] > upper[j]).sum()),
                     'scaler_center': scaler.center_[j], 'scaler_scale': scaler.scale_[j],
                     'score': float(variance[f])})
    return {'selection_order': selected, 'features': [f for f in frame if f in selected],
            'preprocessing': prep, 'correlations': pairs, 'steps': steps}


def normalize(z):
    z = np.asarray(z, dtype=float)
    if z.ndim != 2 or not np.isfinite(z).all():
        raise ValueError('expected finite vector matrix')
    maximum = np.abs(z).max(axis=1)
    nz = maximum != 0
    unit = np.zeros_like(z)
    norm = np.zeros(len(z))
    dominance = np.full(len(z), np.nan)
    index = np.full(len(z), -1, dtype=int)
    ties = np.zeros(len(z), dtype=int)
    t = z[nz] / maximum[nz, None]
    q = (t * t).sum(axis=1)
    unit[nz] = t / np.sqrt(q[:, None])
    norm[nz] = maximum[nz] * np.sqrt(q)
    dominance[nz] = 1 / q
    index[nz] = np.abs(z[nz]).argmax(axis=1)
    ties[nz] = (np.abs(z[nz]) == maximum[nz, None]).sum(axis=1)
    if not np.isfinite(norm).all():
        raise ValueError('vector norm overflow')
    return dict(zero=~nz, unit=unit, norm=norm, dominance=dominance, max_index=index, ties=ties)


def fit_vectors(x):
    x = np.asarray(x, dtype=float)
    if not np.isfinite(x).all():
        raise ValueError('nonfinite fit input')
    q25, q75 = np.percentile(x, [25, 75], axis=0, method='linear')
    center, scale = np.median(x, axis=0), q75 - q25
    if np.any(scale <= 0):
        raise ValueError('nonpositive raw IQR')
    lower, upper = q25 - 3 * scale, q75 + 3 * scale
    xc = np.clip(x, lower, upper)
    return dict(center=center, scale=scale, lower=lower, upper=upper,
                main_z=(x-center)/scale, clip_z=(xc-center)/scale, clipped=xc,
                flags=np.where(x < lower, -1, np.where(x > upper, 1, 0)))


def neighbors(c, ids, k):
    if len(set(ids)) != len(ids) or not 0 < k < len(ids):
        raise ValueError('invalid neighbor population or k')
    return np.array([sorted((j for j in range(len(ids)) if j != i),
                           key=lambda j: (-c[i, j], ids[j]))[:k] for i in range(len(ids))])


def clip_comparison(main, clip, ids, exposed):
    n = len(ids)
    upper = np.triu_indices(n, 1)
    rank = dict(defined=True, n_common=n, n_pairs=n*(n-1)//2,
                n_s_fit_groups_with_clipped_value=int(exposed.sum()), reason='',
                rho=float(spearmanr(main[upper], clip[upper]).statistic))
    rows, summaries = [], []
    for k in (5, 10, 20):
        if n <= k:
            continue
        a, b = neighbors(main, ids, min(k+1, n-1)), neighbors(clip, ids, min(k+1, n-1))
        counts = np.array([len(set(x[:k]) & set(y[:k])) for x, y in zip(a, b)])
        ta = np.array([k < n-1 and main[i, x[k-1]] == main[i, x[k]] for i, x in enumerate(a)])
        tb = np.array([k < n-1 and clip[i, x[k-1]] == clip[i, x[k]] for i, x in enumerate(b)])
        for i, g in enumerate(ids):
            rows.append(dict(g_cd=g, k=k, intersection=int(counts[i]), overlap=float(counts[i]/k),
                             ties_at_k_main=bool(ta[i]), ties_at_k_clip=bool(tb[i]),
                             has_clipped_value=bool(exposed[i])))
        for name, mask in [('all', np.ones(n, bool)), ('has_clipped_true', exposed),
                           ('has_clipped_false', ~exposed)]:
            values = counts[mask]/k
            summaries.append(dict(k=k, subset=name, n=len(values),
                                  mean=float(values.mean()) if len(values) else None,
                                  median=float(np.median(values)) if len(values) else None,
                                  p10=float(np.quantile(values, .1)) if len(values) else None,
                                  min=float(values.min()) if len(values) else None))
    return dict(pair_rank=rank, by_group=rows, summary=summaries)


def dominance(rows, features, mask):
    s, j = rows['dominance'][mask], rows['max_index'][mask]
    q = np.quantile(s, [.25, .5, .75], method='linear')
    summary = dict(n=len(s), p=len(features), one_over_p=1/len(features),
                   s_min=float(s.min()), s_q25=q[0], s_median=q[1], s_q75=q[2], s_max=float(s.max()),
                   n_s_ge_0_5=int((s >= .5).sum()), n_s_ge_0_8=int((s >= .8).sum()))
    by = [dict(feature=f, n_dominant=int((j == i).sum()),
               n_dominant_s_ge_0_5=int(((j == i) & (s >= .5)).sum()),
               n_dominant_s_ge_0_8=int(((j == i) & (s >= .8)).sum())) for i, f in enumerate(features)]
    return dict(summary=summary, by_feature=by)


def fixed_pairs(ids, c):
    n = len(ids)
    if len(set(ids)) != n or c.shape != (n, n) or not np.isfinite(c).all():
        raise ValueError('invalid pair population')
    if np.max(np.abs(c-c.T), initial=0) > ATOL or np.max(np.abs(c), initial=0) > 1+ATOL:
        raise ValueError('invalid cosine symmetry or range')
    pos = {g: i for i, g in enumerate(ids)}
    codes = sorted(ids)
    pairs = sorted([(float(c[pos[a], pos[b]]), a, b) for i, a in enumerate(codes)
                    for b in codes[i+1:]], key=lambda p: (-p[0], p[1], p[2]))
    p = len(pairs)
    b = (p+99)//100
    starts = [1, (p-b)//2+1, p-b+1]
    bands = {level: [start, start+b-1] for level, start in zip(('high','middle','low'), starts)}
    if not p:
        return dict(status='undetermined', reasons=['too_few_groups'], N=n, P=0, B=0, bands={}, picks=[])
    values = np.array([x[0] for x in pairs])
    picks, reasons = [], []
    for level, (start, _) in bands.items():
        ranks = [1] if b < 2 else [(b+2)//3, (2*b+2)//3]
        if b < 2:
            reasons.append('band_short:'+level)
        for j, offset in enumerate(ranks, 1):
            rank = start+offset-1
            v, a, other = pairs[rank-1]
            picks.append(dict(level=level, j=j, rank=rank, a=a, b=other, cosine=v,
                              ties=int((values == v).sum())-1))
    if starts[0]+b > starts[1] or starts[1]+b > starts[2]:
        reasons.append('bands_overlap')
    if len({(x['a'], x['b']) for x in picks}) < len(picks):
        reasons.append('pair_in_multiple_levels')
    if len({x['cosine'] for x in picks}) == 1:
        reasons.append('no_value_difference')
    ok = not any(r in reasons for r in ('bands_overlap','pair_in_multiple_levels','no_value_difference'))
    return dict(status='ok' if ok else 'undetermined', reasons=reasons, N=n, P=p, B=b,
                bands=bands, picks=picks if ok else [])


def calculate(data):
    raw = table(data/'features_800.tsv')
    registry = table(data/'candidate_registry.tsv')
    old = [r['feature'] for r in registry]
    if len(old) != 39 or len(set(old)) != 39 or list(raw[0]) != ['g_cd']+old:
        raise ValueError('39 indicator schema mismatch')
    candidates = [r['feature'] for r in registry if r['category'] == 'candidate']
    if len(candidates) != 29:
        raise ValueError('candidate population mismatch')
    frame = pd.DataFrame([[float(r[f]) if r[f] else np.nan for f in old] for r in raw],
                         columns=old, index=[r['g_cd'] for r in raw])
    quality = pd.DataFrame(table(data/'quality.tsv')).set_index('g_cd')
    s_sel = eligible(frame, quality, candidates)
    selection = select_features(frame.loc[s_sel, candidates])
    if selection['features'] != FEATURES:
        raise ValueError('selection differs from adopted feature set/order')
    s_fit = eligible(frame, quality, FEATURES)
    x = frame.loc[s_fit, FEATURES].to_numpy()
    fit = fit_vectors(x)
    main, clip = normalize(fit['main_z']), normalize(fit['clip_z'])
    m, common = ~main['zero'], ~main['zero'] & ~clip['zero']
    ids = np.array(s_fit)
    cm = main['unit'][m] @ main['unit'][m].T
    cc = clip['unit'][common] @ clip['unit'][common].T
    main_common = cm[np.ix_(common[m], common[m])]
    selection['S_sel'] = s_sel
    result = dict(selection=selection, features=FEATURES, S_fit=s_fit, S=ids[m].tolist(),
                  S_common_clip=ids[common].tolist(),
                  fit={k: fit[k].tolist() for k in ('center','scale','lower','upper')},
                  main_vectors=dict(ids=s_fit, z=fit['main_z'].tolist(), norm=main['norm'].tolist(),
                                    s=main['dominance'].tolist(), max_index=main['max_index'].tolist(), ties=main['ties'].tolist()),
                  clip_vectors=dict(ids=s_fit, z=fit['clip_z'].tolist(), norm=clip['norm'].tolist(),
                                    s=clip['dominance'].tolist(), max_index=clip['max_index'].tolist(), ties=clip['ties'].tolist(), flags=fit['flags'].tolist()),
                  clip=clip_comparison(main_common, cc, ids[common].tolist(), (fit['flags'][common] != 0).any(axis=1)),
                  dominance={name: dominance(rows, FEATURES, mask) for name, rows, mask in [('main',main,m),('clip',clip,common)]},
                  fixed_pairs=fixed_pairs(ids[m].tolist(), cm))
    v = cm[np.triu_indices(len(cm), 1)]
    result['distribution'] = dict(P=len(v), min=float(v.min()), max=float(v.max()),
        max_asymmetry=float(np.abs(cm-cm.T).max()), max_range_excess=max(0., float(np.abs(v).max()-1)),
        quantiles={str(q): float(np.quantile(v,q)) for q in (0.,.01,.05,.25,.5,.75,.95,.99,1.)})
    return result, cm, cc


def compare(actual, expected, path='result'):
    """Exact structural/discrete comparison; tolerance applies only to floats."""
    differences, max_error = [], 0.
    def visit(a, b, key):
        nonlocal max_error
        if isinstance(b, dict):
            if not isinstance(a, dict) or a.keys() != b.keys():
                differences.append(key+': keys differ')
                return
            for k in b:
                visit(a[k], b[k], key+'.'+k)
        elif isinstance(b, list):
            if not isinstance(a, list) or len(a) != len(b):
                differences.append(key+': length differs')
                return
            for i, (x, y) in enumerate(zip(a, b)):
                visit(x, y, f'{key}[{i}]')
        elif isinstance(b, float):
            err = abs(a-b)
            max_error = max(max_error, err)
            if not np.isclose(a, b, atol=ATOL, rtol=RTOL):
                differences.append(f'{key}: {a!r} != {b!r}')
        elif a != b:
            differences.append(f'{key}: {a!r} != {b!r}')
    visit(actual, expected, path)
    return dict(passed=not differences, max_abs_error=max_error, differences=differences)


def ranking_diagnostics(actual, expected, ids, ks=(5, 10, 20)):
    """Describe exact rank mismatches; near ties never change verification status."""
    diagnostics = []
    for k in ks:
        if k >= len(ids)-1:
            continue
        a, b = neighbors(actual, ids, k+1), neighbors(expected, ids, k+1)
        for i in range(len(ids)):
            if np.array_equal(a[i, :k], b[i, :k]):
                continue
            ga = float(actual[i, a[i, k-1]]-actual[i, a[i, k]])
            gb = float(expected[i, b[i, k-1]]-expected[i, b[i, k]])
            changed = sorted(set(a[i, :k]) ^ set(b[i, :k]))
            diagnostics.append(dict(g_cd=ids[i], k=k,
                actual_ids=[ids[j] for j in a[i, :k]], expected_ids=[ids[j] for j in b[i, :k]],
                actual_boundary_gap=ga, expected_boundary_gap=gb,
                near_tie=bool(abs(ga) <= ATOL or abs(gb) <= ATOL),
                swapped_values=[dict(g_cd=ids[j], actual=float(actual[i,j]),
                                     expected=float(expected[i,j])) for j in changed]))
    return diagnostics


def verify_rankings(actual, expected, ids):
    differences = ranking_diagnostics(actual, expected, ids)
    return dict(passed=not differences, differences=differences)


def run(data, output):
    data, output = Path(data), Path(output)
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads((data/'manifest.json').read_text())
    for name, sha in manifest['files'].items():
        if hashlib.sha256((data/name).read_bytes()).hexdigest() != sha:
            raise ValueError('input SHA mismatch: '+name)
    result, cm, cc = calculate(data)
    expected = json.loads((data/'expected/results.json').read_text())
    check = compare(result, expected)
    reference = np.load(data/'expected/similarity_main_800.npy', allow_pickle=False)
    check['similarity_max_abs_error'] = float(np.max(np.abs(cm-reference)))
    check['passed'] &= cm.shape == reference.shape and bool(np.allclose(cm, reference, atol=ATOL, rtol=RTOL))
    if result['S'] == expected['S']:
        check['main_rank_order'] = verify_rankings(cm, reference, result['S'])
        check['passed'] &= check['main_rank_order']['passed']
    if result['S_common_clip'] == expected['S_common_clip']:
        # Reference vectors are used only here, after the new calculation.
        ez = np.array(expected['clip_vectors']['z'])
        erows = normalize(ez)
        keep = [expected['S_fit'].index(g) for g in expected['S_common_clip']]
        eu = erows['unit'][keep]
        check['clip_rank_order'] = verify_rankings(cc, eu @ eu.T, result['S_common_clip'])
        check['passed'] &= check['clip_rank_order']['passed']
    output.mkdir(parents=True, exist_ok=False)
    (output/'results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    np.save(output/'similarity_main_800.npy', cm)
    np.save(output/'similarity_clip_800.npy', cc)
    (output/'verification.json').write_text(json.dumps(check, indent=2)+'\n')
    if not check['passed']:
        raise ValueError('saved-result mismatch; see verification.json')
    return check


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.data, args.output), indent=2))
