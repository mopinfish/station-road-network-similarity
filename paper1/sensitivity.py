"""Paper 1 sensitivity from saved F8 metrics and fixed adopted scales.

This entry starts after road measurement and scale fitting. It does not import
private research code. Exact ties use ascending string IDs; near ties are never
silently accepted. See verification.json for every saved-result comparison.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

for _name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '1'
import numpy as np
from scipy.stats import spearmanr

ATOL = 1e-12
BINS = ['lt_0_5', 'ge_0_5_lt_0_8', 'ge_0_8']


def read_tsv(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f, delimiter='\t'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def write_tsv(path, records):
    if not records:
        return
    with Path(path).open('w') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]), delimiter='\t')
        writer.writeheader()
        writer.writerows({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in r.items()} for r in records)


def transform(x, center, scale):
    x, center, scale = map(lambda a: np.asarray(a, dtype=float), (x, center, scale))
    if not (np.isfinite(x).all() and np.isfinite(center).all() and np.isfinite(scale).all() and (scale > 0).all()):
        raise ValueError('nonfinite metrics/centers or nonpositive scale')
    return (x - center) / scale


def normalize(z):
    z = np.asarray(z, dtype=float)
    if z.ndim != 2 or not np.isfinite(z).all() or np.any(np.all(z == 0, axis=1)):
        raise ValueError('invalid or zero feature vector')
    m = np.max(np.abs(z), axis=1)
    t = z / m[:, None]
    root = np.sqrt(np.sum(t*t, axis=1))
    norm = m * root
    if not np.isfinite(norm).all():
        raise ValueError('norm overflow')
    return t / root[:, None], norm


def top(values, ids, allowed, k):
    positions = np.flatnonzero(allowed)
    if len(positions) < k:
        raise ValueError('fewer than k eligible neighbors')
    ordered = positions[np.lexsort((np.asarray(ids)[positions], -values[positions]))]
    cutoff = values[ordered[k-1]]
    return {'ids': [ids[j] for j in ordered[:k]],
            'values': values[ordered[:k]].tolist(), 'M': len(ordered),
            'boundary_tie': bool(len(ordered)>k and cutoff == values[ordered[k]]),
            'kth_ties': int(np.count_nonzero(values[positions] == cutoff)),
            'boundary_gap': float(cutoff-values[ordered[k]]) if len(ordered)>k else None}


def distance_matrix(ids, records):
    index = {g: i for i, g in enumerate(ids)}
    if len(index) != len(ids):
        raise ValueError('duplicate IDs')
    result = np.full((len(ids), len(ids)), np.nan)
    np.fill_diagonal(result, 0.)
    for r in records:
        a, b = index[r['g_i']], index[r['g_j']]
        d = float(r['d_origin_plane_m'])
        if a == b or np.isfinite(result[a, b]) or not np.isfinite(d) or d < 0:
            raise ValueError('invalid/duplicate distance pair')
        result[a,b] = result[b,a] = d
    if not np.isfinite(result).all():
        raise ValueError('missing distance pair')
    return result


def describe(x):
    x = np.asarray(x, dtype=float)
    if not len(x):
        return {k: None for k in ['mean','q1','median','q3','iqr']}
    q1, median, q3 = np.quantile(x, [.25, .5, .75], method='linear')
    return dict(mean=float(np.mean(x)),q1=float(q1),median=float(median),q3=float(q3),iqr=float(q3-q1))


def dominance(z, features):
    m = np.max(np.abs(z), axis=1)
    maxima = np.abs(z) == m[:,None]
    if np.any(maxima.sum(axis=1) != 1):
        raise ValueError('dominant feature is not unique')
    s = 1 / np.sum((z/m[:,None])**2, axis=1)
    return ([features[j] for j in np.argmax(maxima,axis=1)],
            [BINS[0] if v < .5 else BINS[1] if v < .8 else BINS[2] for v in s], s)


def compare_value(actual, expected, atol=ATOL):
    if isinstance(actual, str) and isinstance(expected, str):
        return actual == expected
    if isinstance(expected, str):
        if expected.lower() in ('true','false'):
            expected = expected.lower() == 'true'
        elif expected in ('', 'NA'):
            return actual is None
        else:
            try:
                expected = float(expected) if any(c in expected.lower() for c in ('.','e')) else int(expected)
            except ValueError:
                return actual == expected
    if isinstance(expected, (bool, int)):
        return actual == expected
    if isinstance(expected, float):
        return actual is not None and bool(np.isclose(actual, expected, atol=atol, rtol=0))
    return actual == expected


class Checks:
    def __init__(self):
        self.count = 0
        self.failures = []
    def equal(self, label, actual, expected, atol=ATOL, audit=None):
        self.count += 1
        if not compare_value(actual, expected, atol):
            failure = {'field':label,'actual':actual,'expected':expected}
            if audit:
                failure['neighbor_audit'] = audit
                gaps = [v['boundary_gap'] for v in audit.values() if isinstance(v, dict) and 'boundary_gap' in v and v['boundary_gap'] is not None]
                failure['classification'] = 'possible_near_tie' if gaps and max(gaps)<=ATOL else 'implementation_or_specification_mismatch'
            self.failures.append(failure)
    def fields(self, label, actual, expected, columns=None, audit=None):
        for k in columns or expected:
            self.equal(f'{label}/{k}', actual.get(k), expected[k], audit=audit)


def overlap_rows(left, right, ids, dist, k, threshold=None):
    records=[]
    for i,g in enumerate(ids):
        eligible = np.arange(len(ids)) != i
        if threshold is not None:
            eligible &= dist[i] > threshold
        a, b = top(left[i],ids,eligible,k), top(right[i],ids,eligible,k)
        common=len(set(a['ids']) & set(b['ids']))
        records.append({'g_cd':g,'k':k,'M':a['M'],'intersection':common,'overlap':common/k,
                        'ties_left':a['boundary_tie'],'ties_right':b['boundary_tie'], 'left':a,'right':b})
    return records


def pair_values(left, right, dist=None, threshold=None):
    ii,jj=np.triu_indices(len(left),1)
    if threshold is not None:
        mask=dist[ii,jj]>threshold;ii,jj=ii[mask],jj[mask]
    a,b=left[ii,jj],right[ii,jj]
    delta=b-a
    return {'n_pairs':len(a),'spearman':float(spearmanr(a,b).statistic),
            'main':describe(a),'park':describe(b),'delta':describe(delta),'abs_delta':describe(np.abs(delta))}


def phase_summary(before, after):
    x=np.array([r['overlap'] for r in before]);y=np.array([r['overlap'] for r in after]);d=y-x
    m=np.array([r['M'] for r in after])
    out={'n':len(x),'k':before[0]['k'],'M_before':before[0]['M'],
         'M_after_min':int(m.min()),'M_after_median':float(np.median(m)),'M_after_max':int(m.max()),
         'delta_negative_n':int(sum(d<0)),'delta_zero_n':int(sum(d==0)),'delta_positive_n':int(sum(d>0))}
    for prefix,vals in [('overlap_before',x),('overlap_after',y),('delta',d),('delta_after_minus_before',d)]:
        out.update({prefix+'_'+k:v for k,v in describe(vals).items()})
    return out


def table_cells(before, after, pairs, clip, dom, norm, park, zscores, features):
    """Only adopted paper cells, distinct from the larger S3 audit."""
    cells=[]
    def put(key,value,digits):
        display=str(int(value)) if digits==0 else format(value, '.'+str(digits)+'f') if isinstance(digits,int) else str(float(value))
        cells.append({'cell':key,'value':float(value),'display':display})
    put('table6/clip/rho',pairs['clip']['spearman'],3)
    for k in [5,10,20]:
        allrow=next(r for r in clip if r['subset']=='all' and r['k']==k)
        clipped=next(r for r in clip if r['subset']=='has_clipped_true' and r['k']==k)
        for label,value,digits in [('all_mean',allrow['overlap_before_mean'],3),('all_median',allrow['overlap_before_median'],None),('reference',k/613,4)]:
            put(f'table6/clip/{k}/{label}',value,digits)
        for phase in ['before','after']:
            for stat,digits in [('mean',3),('median',None)]:
                put(f'table6/clip/{k}/clipped_{phase}_{stat}',clipped[f'overlap_{phase}_{stat}'],digits)
    for condition,name in [('main','robust__F8'),('clip','clip')]:
        _,_,s=dominance(zscores[name],features)
        for stat,value,digits in [('n',len(s),0),('median',np.median(s),3),('ge_0_5',sum(s>=.5),0),('ge_0_8',sum(s>=.8),0)]:
            put(f'table6/s/{condition}/{stat}',value,digits)
    for row in dom:
        if row['dominant_feature'] is not None or row['bin']=='all':continue
        key='table6/dominance/'+row['bin'];put(key+'/n',row['n'],0)
        for phase in ['before','after']:
            for stat,digits in [('mean',3),('median',None)]:
                put(f'{key}/{phase}_{stat}',row[f'overlap_{phase}_{stat}'],digits)
    for label in ['range_600_800','range_800_1000','range_600_1000','scaler__F8']:
        put('table7/'+label+'/n',len(before[label,10]),0)
        put('table7/'+label+'/rho',pairs[label]['spearman'],3)
        for phase,store in [('before',before),('after',after)]:
            put('table7/'+label+'/'+phase,np.mean([r['overlap'] for r in store[label,10]]),3)
    for scaler in ['robust','standard']:
        labels=[scaler+'__exclude__'+f for f in features];put('table7/'+scaler+'/n',len(before[labels[0],10]),0)
        metrics={'rho':[pairs[label]['spearman'] for label in labels], 'before':[np.mean([r['overlap'] for r in before[label,10]]) for label in labels]}
        if scaler=='robust':metrics['after']=[np.mean([r['overlap'] for r in after[label,10]]) for label in labels]
        for metric,values in metrics.items():
            put('table7/'+scaler+'/'+metric+'_min',min(values),3);put('table7/'+scaler+'/'+metric+'_max',max(values),3)
    for row in norm:put(f"table7/norm/{row['comparison_id']}/{row['k']}",row['rho'],3)
    for condition,phases in park.items():
        for phase,row in phases.items():
            key=f'table8/{condition}/{phase}'
            put(key+'/n_pairs',row['n_pairs'],0);put(key+'/rho',row['spearman'],3)
            put(key+'/overlap_mean',row['overlap']['mean'],3);put(key+'/overlap_median',row['overlap']['median'],None)
            for side in ['main','park']:
                for stat in ['median','iqr']:put(f'{key}/{side}_{stat}',row[side][stat],4)
            for stat in ['median','q3']:put(f'{key}/abs_delta_{stat}',row['abs_delta'][stat],4)
    return cells


def run(data, output):
    data,output=Path(data),Path(output)
    if output.exists():
        raise FileExistsError(output)
    manifest=json.loads((data/'manifest.json').read_text())
    for filename,pin in manifest['files'].items():
        raw=(data/filename).read_bytes()
        if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('input hash mismatch: '+filename)
    cfg=json.loads((data/'settings.json').read_text()); F=cfg['features']; all_ids=cfg['ids']
    if len(F)!=8 or len(set(F))!=8 or len(all_ids)!=614 or all_ids!=sorted(set(all_ids)):
        raise ValueError('paper1 feature/ID contract mismatch')
    checks=Checks(); matrices={}; station_ids={}; zscores={}; norms={}
    def raw_table(name, ids):
        rows=read_tsv(data/name)
        if [r['g_cd'] for r in rows]!=ids or set(rows[0])!=set(['g_cd']+F):
            raise ValueError('ID/column contract mismatch: '+name)
        return np.array([[float(r[f]) for f in F] for r in rows])
    def add(name, ids, z):
        u,norm=normalize(z);matrices[name]=u@u.T;station_ids[name]=ids;zscores[name]=z;norms[name]=norm
    x800=raw_table('features_800.tsv',all_ids)
    for name,scale in cfg['scales'].items():
        radius=name.removeprefix('range_') if name.startswith('range_') else '800'
        ids=cfg['range_ids'][radius]; x=x800 if radius=='800' else raw_table('features_'+radius+'.tsv',ids)
        columns=[F.index(f) for f in scale['features']]
        add(name, ids, transform(x[:,columns],scale['center'],scale['scale']))
    matrices['range_800']=matrices['robust__F8'];station_ids['range_800']=all_ids
    main_scale=cfg['scales']['robust__F8']
    lower=np.array([cfg['clip_bounds']['lower'][f] for f in F]);upper=np.array([cfg['clip_bounds']['upper'][f] for f in F])
    clipped=np.clip(x800,lower,upper);clipped_ids={g for g,changed in zip(all_ids,np.any(clipped!=x800,axis=1)) if changed}
    checks.equal('clipped_subset_n',len(clipped_ids),43)
    add('clip',all_ids,transform(clipped,main_scale['center'],main_scale['scale']))
    for condition,ids in cfg['park_ids'].items():
        add('park_'+condition,ids,transform(raw_table('park_'+condition+'.tsv',ids),main_scale['center'],main_scale['scale']))
    distances=distance_matrix(all_ids,read_tsv(data/'distances.tsv')); all_index={g:i for i,g in enumerate(all_ids)}
    def paired(left,right):
        ids=sorted(set(station_ids[left])&set(station_ids[right])); il=[station_ids[left].index(g) for g in ids]; ir=[station_ids[right].index(g) for g in ids]; di=[all_index[g] for g in ids]
        return matrices[left][np.ix_(il,il)],matrices[right][np.ix_(ir,ir)],ids,distances[np.ix_(di,di)]
    comparisons=[]
    for suffix in ['F8']+['no_'+f for f in F]:
        comparisons.append(('scaler__'+suffix,'robust__'+suffix,'standard__'+suffix))
    for scaler in ['robust','standard']:
        comparisons.extend((scaler+'__exclude__'+f,scaler+'__F8',scaler+'__no_'+f) for f in F)
    comparisons += [('range_600_800','range_600','range_800'),('range_800_1000','range_800','range_1000'),('range_600_1000','range_600','range_1000')]
    before={}; after={}; summaries=[]; audit=[]; pair_summaries={}
    for label,l,r in comparisons+[('clip','robust__F8','clip')]+[('park_'+c,'robust__F8','park_'+c) for c in cfg['park_ids']]:
        left,right,ids,dist=paired(l,r)
        pair_summaries[label]=pair_values(left,right)
        for k in ([10] if label.startswith('park_') else [5,10,20]):
            rows=overlap_rows(left,right,ids,dist,k);before[label,k]=rows
            for row in rows:
                audit.append({'comparison':label,'phase':'before',**row})
        nonnear=(label=='clip' or label.startswith(('park_','range_','robust__exclude__')) or label=='scaler__F8')
        if nonnear:
            threshold=2000 if '1000' in label else 1600
            for k in ([5,10,20] if label=='clip' else [10]):
                rows=overlap_rows(left,right,ids,dist,k,threshold);after[label,k]=rows
                summaries.append({'comparison_id':label,'threshold_m':threshold,**phase_summary(before[label,k],rows)})
                for row in rows:
                    audit.append({'comparison':label,'phase':'after',**row})
            if label.startswith('park_'):
                pair_summaries[label+'_after']=pair_values(left,right,dist,threshold)
    output.mkdir(parents=True)
    # Compare computed records against independent saved references, never populate results from them.
    E=data/'expected'
    station_index={(label,k,r['g_cd']):r for (label,k),rows in before.items() for r in rows}
    after_index={(label,k,r['g_cd']):r for (label,k),rows in after.items() for r in rows}
    for ref in json.loads((E/'candidate_ids.json').read_text()):
        store=station_index if ref['phase']=='before' else after_index
        row=store[ref['comparison'],ref['k'],ref['g_cd']][ref['side']]
        label='/'.join([ref['comparison'],ref['phase'],ref['g_cd'],ref['side']])
        checks.equal('candidates/'+label,row['ids'],ref['ids'],audit={'computed':row,'saved':{'ids':ref['ids'],'values':ref['values']}})
        checks.equal('candidate_values/'+label,bool(np.allclose(row['values'],ref['values'],rtol=0,atol=ATOL)),True)
    for ref in read_tsv(E/'s3_comparisons.tsv'):
        label=ref['comparison_id'];rows=before[label,10]
        checks.fields(label,{'n_common':len(rows),'n_pairs':pair_summaries[label]['n_pairs'],'rho':pair_summaries[label]['spearman']},ref,['n_common','n_pairs','rho'])
    for ref in read_tsv(E/'s3_stations.tsv'):
        key=(ref['comparison_id'],int(ref['k']),ref['g_cd']);r=station_index[key]
        checks.fields(str(key),{'intersection':r['intersection'],'overlap':r['overlap'],'ties_at_k_left':r['ties_left'],'ties_at_k_right':r['ties_right']},ref,['intersection','overlap','ties_at_k_left','ties_at_k_right'],audit={'left':r['left'],'right':r['right']})
    for ref in read_tsv(E/'s3_summary.tsv'):
        label,k=ref['comparison_id'],int(ref['k']);rows=before[label,k];v=np.array([r['overlap'] for r in rows])
        actual={'n_common':len(rows),'M':len(rows)-1,'reference_k_over_M':k/(len(rows)-1),
                'overlap_mean':float(v.mean()),'overlap_median':float(np.median(v)),'overlap_p10':float(np.quantile(v,.1)), 'overlap_min':float(v.min()),
                'n_ties_at_k_left':sum(r['ties_left'] for r in rows),'n_ties_at_k_right':sum(r['ties_right'] for r in rows)}
        checks.fields(label+'/'+str(k),actual,ref,list(actual))
    norm_results=[]
    for ref in read_tsv(E/'norm_overlap.tsv'):
        label,k=ref['comparison_id'],int(ref['k']);rows=before[label,k]
        rho=float(spearmanr([norms['robust__F8'][all_index[r['g_cd']]] for r in rows],[r['overlap'] for r in rows]).statistic)
        checks.equal('norm/'+label+'/'+str(k),rho,ref['rho']);norm_results.append({'comparison_id':label,'k':k,'n':len(rows),'rho':rho})
    for filename,default in [('range_stations.tsv',None),('scale_stations.tsv',None),('clip_stations.tsv','clip')]:
        for ref in read_tsv(E/filename):
            label=default or ref['comparison_id'];k=int(ref['k']);g=ref['g_cd'];b=station_index[label,k,g];a=after_index[label,k,g]
            actual={'M_before':b['M'],'M_after':a['M'],'intersection_before':b['intersection'],'intersection_after':a['intersection'],'overlap_before':b['overlap'],'overlap_after':a['overlap'],'delta_after_minus_before':a['overlap']-b['overlap']}
            for phase,row in [('before',b),('after',a)]:
                for side in ['left','right']:
                    actual['ties_'+side+'_'+phase]=row['ties_'+side]
                actual['ties_main_'+phase]=row['ties_left'];actual['ties_clip_'+phase]=row['ties_right']
            if default:
                actual['has_clipped_value']=g in clipped_ids
            checks.fields(filename+'/'+g+'/'+str(k),actual,ref,[c for c in ref if c in actual],audit={'left':a['left'],'right':a['right']})
    for filename in ['range_summary.tsv','scale_summary.tsv']:
        for ref in read_tsv(E/filename):
            actual=next(r for r in summaries if r['comparison_id']==ref['comparison_id'] and r['k']==int(ref['k']))
            checks.fields(filename+'/'+ref['comparison_id'],actual,ref)
    clip_summary=[]
    for ref in read_tsv(E/'clip_summary.tsv'):
        k=int(ref['k']);b=before['clip',k];a=after['clip',k]
        if ref['subset']!='all':
            wanted=ref['subset']=='has_clipped_true'
            b=[r for r in b if (r['g_cd'] in clipped_ids)==wanted];a=[r for r in a if (r['g_cd'] in clipped_ids)==wanted]
        actual=phase_summary(b,a);actual['subset']=ref['subset'];actual['reference_before_mean']=float(np.mean([k/r['M'] for r in b]));actual['reference_after_mean']=float(np.mean([k/r['M'] for r in a]))
        checks.fields('clip_summary/'+ref['subset']+'/'+str(k),actual,ref);clip_summary.append(actual)
    # Dominance bins retain the original saved assignments after an independent numerical check.
    labels,bins,s=dominance(zscores['robust__F8'],F); saved=read_tsv(data/'dominance.tsv')
    if [r['g_cd'] for r in saved]!=all_ids:
        raise ValueError('dominance ID contract')
    dom=[]
    for i,ref in enumerate(saved):
        g=ref['g_cd'];checks.equal('dominance/s/'+g,float(s[i]),float(ref['s']),1e-14);checks.equal('dominance/feature/'+g,labels[i],ref['s_feature']);checks.equal('dominance/ties/'+g,1,int(ref['s_ties']))
        fixed_s=float(ref['s']);bucket=BINS[0] if fixed_s<.5 else BINS[1] if fixed_s<.8 else BINS[2]
        label='robust__exclude__'+ref['s_feature'];b=station_index[label,10,g];a=after_index[label,10,g]
        dom.append({'g_cd':g,'s':fixed_s,'dominant_feature':ref['s_feature'],'bin':bucket,'comparison_id':label,'k':10,'M':b['M'],'intersection':b['intersection'],'overlap':b['overlap'],'overlap_before':b['overlap'],'overlap_after':a['overlap'],'delta_after_minus_before':a['overlap']-b['overlap']})
    for ref in read_tsv(E/'dominance_before.tsv'):
        checks.fields('dominance_before/'+ref['g_cd'],dom[all_index[ref['g_cd']]],ref)
    dom_summaries=[]
    for feature in [None]+F:
        for bucket in BINS+(['all'] if feature is None else []):
            rows=[r for r in dom if (bucket=='all' or r['bin']==bucket) and (feature is None or r['dominant_feature']==feature)]
            d=np.array([r['delta_after_minus_before'] for r in rows]);out={'dominant_feature':feature,'bin':bucket,'n':len(rows)}
            out.update(describe([r['overlap'] for r in rows]))
            for phase in ['overlap_before','overlap_after','delta_after_minus_before']:
                out.update({phase+'_'+k:v for k,v in describe([r[phase] for r in rows]).items()})
            out.update(delta_negative_n=int(sum(d<0)),delta_zero_n=int(sum(d==0)),delta_positive_n=int(sum(d>0)));dom_summaries.append(out)
    for filename in ['dominance_bins_before.tsv','dominance_features_before.tsv','dominance_bins_after.tsv']:
        for ref in read_tsv(E/filename):
            actual=next(r for r in dom_summaries if r['bin']==ref['bin'] and r['dominant_feature']==ref.get('dominant_feature'))
            checks.fields(filename+'/'+ref['bin']+'/'+str(ref.get('dominant_feature')),actual,ref)
    park_summary={}
    for c in cfg['park_ids']:
        label='park_'+c;park_summary[c]={}
        for phase,store in [('before',before),('after',after)]:
            vals=pair_summaries[label+('_after' if phase=='after' else '')].copy();ov=[r['overlap'] for r in store[label,10]]
            vals['overlap']={'n':len(ov),'mean':float(np.mean(ov)),'median':float(np.median(ov))};park_summary[c][phase]=vals
    def check_tree(label,actual,expected):
        if isinstance(expected,dict):
            for k,v in expected.items():
                check_tree(label+'/'+k,actual.get(k),v)
        else:
            checks.equal(label,actual,expected)
    expected_park=json.loads((E/'park_summary.json').read_text())
    for c in cfg['park_ids']:
        for phase in ['before','after']:
            check_tree('park/'+c+'/'+phase,park_summary[c][phase],expected_park[c][phase])
    for ref in read_tsv(E/'park_stations.tsv'):
        c,g=ref['condition'],ref['g_cd'];label='park_'+c
        b=station_index[label,10,g];a=after_index[label,10,g]
        checks.equal('park_delta/'+c+'/'+g,a['overlap']-b['overlap'],ref['overlap_delta'])
        for phase,row in [('before',b),('after',a)]:
            actual={'M':row['M'],'overlap':row['overlap'],'main_ids':row['left']['ids'],'park_ids':row['right']['ids'],'ties':[row['left']['kth_ties'],row['right']['kth_ties']]}
            for k,v in actual.items():
                expected=ref[phase+'_'+k];expected=json.loads(expected) if k in ['main_ids','park_ids','ties'] else expected
                checks.equal('park/'+c+'/'+g+'/'+phase+'/'+k,v,expected,audit={'left':row['left'],'right':row['right']})
    r4=json.loads((E/'park_r4.json').read_text());values=json.loads((E/'park_value.json').read_text());examples=[]
    for c,ids in cfg['park_ids'].items():
        label='park_'+c;stats=park_summary[c]['before'];checks.equal(c+'/S_common',ids,r4[c]['S_common'])
        checks.equal(c+'/R4rho',stats['spearman'],r4[c]['result']['spearman_all_pairs'])
        check_tree(c+'/R4overlap',stats['overlap'],r4[c]['result']['topk']['10']['all'])
        check_tree(c+'/value',stats,{k:values[c][k] for k in ['n_pairs','main','park','delta','abs_delta']})
        left,right,ids,dist=paired('robust__F8',label);ref=r4[c]['result']['examples'];ga,gb=ref['pair'];ia,ib=ids.index(ga),ids.index(gb)
        ex={'pair':[ga,gb],'cosine_main':float(left[ia,ib]),'cosine_park':float(right[ia,ib])}
        for key,i,j in [('rank_of_a_for_b',ib,ia),('rank_of_b_for_a',ia,ib)]:
            ex[key]=[top(mat[i],ids,np.arange(len(ids))!=i,len(ids)-1)['ids'].index(ids[j])+1 for mat in [left,right]]
        checks.fields('example/'+c,ex,ref,list(ex));examples.append({'condition':c,**ex})
    cells=table_cells(before,after,pair_summaries,clip_summary,dom_summaries,norm_results,park_summary,zscores,F)
    expected_cells=json.loads((E/'table_cells.json').read_text())
    checks.equal('table_cell_keys',sorted(r['cell'] for r in cells),sorted(expected_cells))
    for cell in cells:checks.equal(cell['cell']+'/display',cell['display'],expected_cells[cell['cell']])
    write_tsv(output/'table_cells.tsv',cells)
    write_tsv(output/'station_comparisons.tsv',audit);write_tsv(output/'nonnear_summary.tsv',summaries);write_tsv(output/'clip_summary.tsv',clip_summary)
    write_tsv(output/'dominance_stations.tsv',dom);write_tsv(output/'dominance_summary.tsv',dom_summaries);write_tsv(output/'norm_overlap.tsv',norm_results)
    write_json(output/'pair_summary.json',pair_summaries);write_json(output/'park_summary.json',park_summary);write_json(output/'park_examples.json',examples)
    write_json(output/'verification.json',{'checks':checks.count,'failures':checks.failures,'passed':not checks.failures,'atol':ATOL,'dominance_s_atol':1e-14,'integer_ID_tie_policy':'exact; near ties never waived'})
    write_json(output/'manifest.json',{'files':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in output.iterdir() if p.is_file()},'numpy':np.__version__,'python':sys.version.split()[0],'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'input_manifest_sha256':hashlib.sha256((data/'manifest.json').read_bytes()).hexdigest(),'blas_threads':1})
    print(json.dumps({'checks':checks.count,'failures':len(checks.failures),'output':str(output)}))
    return 1 if checks.failures else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    return run(args.data,args.output)


if __name__=='__main__':
    sys.exit(main())
