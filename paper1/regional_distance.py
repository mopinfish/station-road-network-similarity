"""Paper 1 regional summaries and conditional distance prediction from saved inputs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import warnings

import numpy as np
from scipy.optimize import curve_fit, OptimizeWarning
from scipy.stats import spearmanr
from threadpoolctl import threadpool_info

MODELS = {
    'linear': (lambda d,a,b: a+b*d, [.2,-.005], ['mean',0], [-2,-1], [2,1]),
    'exponential': (lambda d,a,b,c: a*np.exp(-b*d)+c, [.5,.05,0], [1,.01,-.2], [0,.001,-2], [3,1,2]),
    'power': (lambda d,a,b,c: a*(d+.1)**(-b)+c, [1,.3,0], [.5,.1,-.2], [0,.01,-2], [10,3,2]),
    'logarithmic': (lambda d,a,b: a-b*np.log(d+.1), [.3,.05], [0,.01], [-2,0], [2,2]),
}


def read_tsv(path):
    with Path(path).open() as f:
        return list(csv.DictReader(f, delimiter='\t'))


def write_tsv(path, rows):
    with Path(path).open('w') as f:
        writer = csv.DictWriter(f, list(rows[0]), delimiter='\t', lineterminator='\n')
        writer.writeheader()
        writer.writerows([{k: ('true' if v else 'false') if isinstance(v,(bool,np.bool_)) else v for k,v in r.items()} for r in rows])


def summary(x):
    x = np.asarray(x)
    q = np.quantile(x,[.25,.5,.75],method='linear') if len(x) else [None]*3
    return dict(n=len(x),n_missing=0,q1=q[0],median=q[1],q3=q[2],iqr=q[2]-q[0] if len(x) else None)


def rank_groups(x):
    order = np.argsort(x,kind='mergesort')
    starts = np.r_[0,np.flatnonzero(np.diff(np.asarray(x)[order]) != 0)+1]
    return order, starts


def weighted_rho(weights, plans):
    ranks=[]
    for order, starts in plans:
        mass=np.add.reduceat(weights[order],starts)
        mid=np.r_[0.,np.cumsum(mass[:-1])]+(mass+1)/2
        rank=np.empty(len(weights))
        rank[order]=np.repeat(mid,np.diff(np.r_[starts,len(weights)]))
        ranks.append(rank)
    keep=weights>0
    if keep.sum()<2:
        return float('nan')
    w=weights[keep]
    x,y=[r[keep] for r in ranks]
    x=x-np.dot(w,x)/w.sum()
    y=y-np.dot(w,y)/w.sum()
    den=np.sqrt(np.dot(w,x*x)*np.dot(w,y*y))
    return float(np.dot(w,x*y)/den) if den else float('nan')


def bootstrap(n,i,j,d,y,seeds):
    plans=rank_groups(d),rank_groups(y)
    rows=[]
    for seed in seeds:
        counts=np.bincount(np.random.Generator(np.random.PCG64(seed)).integers(0,n,size=n),minlength=n).astype(float)
        w=counts[i]*counts[j]
        rho=weighted_rho(w,plans)
        positive=int((w>0).sum())
        reason='' if np.isfinite(rho) else ('fewer than two pairs carry a positive weight' if positive<2 else 'a weighted rank vector has zero variance or is non-finite')
        rows.append(dict(seed=seed,rho=rho if np.isfinite(rho) else None,defined=bool(np.isfinite(rho)),reason=reason,distinct_stations=int((counts>0).sum()),positive_pairs=positive,weight_sum=float(w.sum())))
    return rows


def folds_for(n,seed):
    labels=np.empty(n,dtype=int)
    for k,part in enumerate(np.array_split(np.random.Generator(np.random.PCG64(seed)).permutation(n),5)):
        labels[part]=k
    return labels


def fold_masks(i,j,labels,k):
    held=labels==k
    return ~held[i]&~held[j],held[i]&held[j]


def fit_model(name,d,y):
    function,initial,retry,lower,upper=MODELS[name]
    reasons=[]
    warning_messages=[]
    for attempt,(p0,limit) in enumerate(((initial,10000),(retry,50000)),1):
        p0=[float(np.mean(y)) if p=='mean' else p for p in p0]
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always',OptimizeWarning)
                params,_=curve_fit(function,d,y,p0=p0,bounds=(lower,upper),method='trf',maxfev=limit,ftol=1e-8,xtol=1e-8,gtol=1e-8)
            warning_messages.extend(f'attempt{attempt}:{w.category.__name__}:{w.message}' for w in caught if issubclass(w.category,OptimizeWarning))
            if not np.isfinite(params).all() or not np.isfinite(function(d,*params)).all():
                raise FloatingPointError('non-finite estimate or prediction')
            return dict(status='ok',attempts=attempt,a=float(params[0]),b=float(params[1]),c=float(params[2]) if len(params)==3 else None,at_bound=bool((np.abs(params-lower)<=1e-8).any() or (np.abs(params-upper)<=1e-8).any()),reason='',warnings=' | '.join(warning_messages))
        except (RuntimeError,ValueError,FloatingPointError,np.linalg.LinAlgError) as error:
            reasons.append(f'attempt{attempt}:{type(error).__name__}:{error}')
    return dict(status='failed',attempts=2,a=None,b=None,c=None,at_bound=False,reason=' | '.join(reasons),warnings=' | '.join(warning_messages))


def cross_validate(n,i,j,d,y,folds):
    records=[]; repeats=[]
    for seed,labels in folds.items():
        for k in range(5):
            train,test=fold_masks(i,j,labels,k)
            null=float(np.mean(y[train]))
            for name in MODELS:
                fit=fit_model(name,d[train],y[train]) if train.sum()>=2 and test.sum() else dict(status='failed',attempts=0,a=None,b=None,c=None,at_bound=False,reason='the fold has too few training or test pairs to fit',warnings='')
                row=dict(model=name,seed=seed,fold=k,n_train_stations=int((labels!=k).sum()),n_test_stations=int((labels==k).sum()),n_train_pairs=int(train.sum()),n_test_pairs=int(test.sum()),train_mean_similarity=null,**fit)
                row.update(sse=None,null_sse=None,n=0,fold_rmse=None,fold_oos_r2=None)
                if fit['status']=='ok':
                    params=[fit[p] for p in ('a','b','c') if fit[p] is not None]
                    prediction=MODELS[name][0](d[test],*params)
                    if not np.isfinite(prediction).all():
                        row.update(status='failed',reason='the fitted model produced a non-finite test prediction')
                    else:
                        residual=y[test]-prediction; centred=y[test]-null
                        sse=float(np.dot(residual,residual)); ns=float(np.dot(centred,centred)); count=int(test.sum())
                        row.update(sse=sse,null_sse=ns,n=count,fold_rmse=float(np.sqrt(sse/count)),fold_oos_r2=1-sse/ns if ns>0 else None)
                records.append(row)
        for name in MODELS:
            group=[r for r in records if r['seed']==seed and r['model']==name]
            valid=[r for r in group if r['status']=='ok']
            sse=sum(r['sse'] for r in valid); ns=sum(r['null_sse'] for r in valid); count=sum(r['n'] for r in valid)
            defined=len(valid)==5 and ns>0 and count>0
            reason='' if defined else 'incomplete folds or undefined null variance'
            repeats.append(dict(model=name,seed=seed,oos_r2=1-sse/ns if defined else None,rmse=float(np.sqrt(sse/count)) if len(valid)==5 and count else None,null_rmse=float(np.sqrt(ns/count)) if count else None,n_valid_folds=len(valid),n_test_pairs=count,status='defined' if defined else 'undefined',defined=defined,reason=reason))
        print(f'CV seed {seed} complete',flush=True)
    summaries=[]
    for name in MODELS:
        fs=[r for r in records if r['model']==name]; rs=[r for r in repeats if r['model']==name]; valid=[r for r in rs if r['defined']]
        failed=sum(r['status']!='ok' for r in fs)
        row=dict(model=name,n_fits=len(fs),n_failed_fits=failed,failure_rate=failed/len(fs),n_at_bound_fits=sum(r['at_bound'] for r in fs),unreliable=failed/len(fs)>.01,n_repeats=len(rs),n_valid_repeats=len(valid),n_excluded_repeats=len(rs)-len(valid),exclusion_reasons=';'.join(sorted({r['reason'] for r in rs if not r['defined']})),status='unavailable' if not valid else ('unreliable' if failed/len(fs)>.01 else 'available'))
        for metric in ('rmse','oos_r2'):
            values=[r[metric] for r in valid]
            for label,q in [('median',.5),('p2_5',.025),('p97_5',.975)]:
                row[metric+'_'+label]=float(np.quantile(values,q,method='linear')) if values else None
        summaries.append(row)
    common=[s for s in folds if all(any(r['seed']==s and r['model']==m and r['defined'] for r in repeats) for m in MODELS)]
    medians={m:float(np.median([r['rmse'] for r in repeats if r['model']==m and r['seed'] in common])) if common else None for m in MODELS}
    eligible=[r['model'] for r in summaries if not r['unreliable'] and medians[r['model']] is not None]
    best=min(eligible,key=medians.get) if eligible else None
    selection=dict(common_seeds=common,common_repeat_count=len(common),common_rmse_median=medians,selected_model=best,equivalent_models=[m for m in eligible if medians[m]<=medians[best]*1.01],equivalence_ratio=1.01)
    return records,repeats,summaries,selection


def compare(actual,expected,tolerance):
    if len(actual)!=len(expected):
        raise ValueError('reference row count mismatch')
    maxdiff=0.; problems=[]
    integer_keys={'seed','fold','distinct_stations','positive_pairs','weight_sum','n','n_missing','n_pairs','excluded_pairs','n_stations','n_inside_stations','n_outside_stations','n_planned','n_finite','n_undefined','attempts'}
    for index,(got,want) in enumerate(zip(actual,expected)):
        for key,value in want.items():
            if key == 'unit':  # Units describe saved inputs, not a recomputed statistic.
                continue
            if key not in got:
                problems.append(dict(row=index,column=key,actual='MISSING',expected=value))
                continue
            observed=got[key]
            if value in ('','NA') and observed is None:
                continue
            if value in ('true','false'):
                ok=bool(observed)==(value=='true')
            else:
                try:
                    diff=abs(float(observed)-float(value)); maxdiff=max(maxdiff,diff)
                    tol=0 if key in integer_keys or key.startswith('n_') else (1e-8 if key in ('a','b','c') else tolerance)
                    ok=diff<=tol
                except (ValueError,TypeError):
                    ok=str(observed)==value
            if not ok:
                problems.append(dict(row=index,column=key,actual=observed,expected=value))
    return dict(max_absolute_difference=maxdiff,mismatches=problems,passed=not problems)


def display_tables(spearman,models):
    table9=[dict(condition=r['condition'],n_pairs=int(r['n_pairs']),rho=f"{float(r['rho']):.3f}",lower=f"{float(r['interval_lower']):.3f}",upper=f"{float(r['interval_upper']):.3f}") for r in spearman]
    columns=('rmse_median','oos_r2_median','oos_r2_p2_5','oos_r2_p97_5')
    table10=[dict(condition=r['condition'],model=r['model'],**{k:f'{float(r[k]):.4f}' for k in columns}) for r in models]
    return {'table9.tsv':table9,'table10.tsv':table10}


def run(data,output):
    if output.exists():
        raise ValueError('output directory already exists')
    pools=[p for p in threadpool_info() if p['user_api']=='blas']
    if not pools or any(p['num_threads']!=8 for p in pools):
        raise ValueError('Start this CLI with OPENBLAS_NUM_THREADS=8 OMP_NUM_THREADS=8 MKL_NUM_THREADS=8; adopted optimizer requires eight BLAS threads. No runtime upscaling is attempted.')
    manifest=json.loads((data/'manifest.json').read_text())
    for name,pin in manifest['files'].items():
        payload=(data/name).read_bytes()
        if len(payload)!=pin['bytes'] or hashlib.sha256(payload).hexdigest()!=pin['sha256']:
            raise ValueError('input manifest mismatch: '+name)
    ids=json.loads((data/'station_ids.json').read_text()); n=len(ids)
    if n!=614 or ids!=sorted(set(ids)):
        raise ValueError('station population/order mismatch')
    C=np.load(data/'similarity_main_800.npy',allow_pickle=False)
    if C.shape!=(n,n) or not np.isfinite(C).all() or not np.allclose(C,C.T,atol=1e-12,rtol=0) or not np.allclose(np.diag(C),1,atol=1e-12,rtol=0) or np.max(np.abs(C))>1+1e-12:
        raise ValueError('similarity matrix invalid')
    pairs=read_tsv(data/'pair_distance.tsv'); i,j=np.triu_indices(n,1)
    if len(pairs)!=len(i) or any(int(r['pair_index'])!=k or (r['g_i'],r['g_j'])!=(ids[a],ids[b]) for k,(r,a,b) in enumerate(zip(pairs,i,j))):
        raise ValueError('distance pair IDs/order mismatch')
    distance=np.array([float(r['d_origin_plane_m']) for r in pairs]); near=distance<=1600
    if not np.isfinite(distance).all() or (distance<0).any() or any((r['excluded']=='true')!=bool(v) for r,v in zip(pairs,near)):
        raise ValueError('distance/near flags invalid')
    features=read_tsv(data/'features_raw.tsv')
    if [r['g_cd'] for r in features]!=ids or any(r['inside'] not in ('true','false') for r in features):
        raise ValueError('membership IDs/flags mismatch')
    inside=np.array([r['inside']=='true' for r in features]); classes=np.where(inside[i]&inside[j],'II',np.where(inside[i]^inside[j],'IO','OO'))
    foldrows=read_tsv(data/'cv_station_folds.tsv'); folds={}
    if len(foldrows)!=n*20:
        raise ValueError('fold row count mismatch')
    for seed in range(3000,3020):
        rows=[r for r in foldrows if int(r['seed'])==seed]
        if [r['g_cd'] for r in rows]!=ids:
            raise ValueError('fold station order mismatch')
        labels=np.array([int(r['fold']) for r in rows])
        if not np.array_equal(labels,folds_for(n,seed)):
            raise ValueError('fold RNG mismatch')
        folds[seed]=labels
    tables={}; regional=[]; feature_stats=[]
    for cls in ('II','IO','OO'):
        base=classes==cls; removed=int((base&near).sum())
        for phase,mask in [('before',base),('after',base&~near)]:
            endpoints=np.unique(np.r_[i[mask],j[mask]])
            regional.append(dict(phase=phase,**{'class':cls},n_pairs=int(mask.sum()),excluded_pairs=removed,excluded_fraction=removed/int(base.sum()),n_stations=len(endpoints),n_inside_stations=int(inside[endpoints].sum()),n_outside_stations=int((~inside[endpoints]).sum()),**summary(C[i[mask],j[mask]])))
    for feature in list(features[0])[2:]:
        values=np.array([float(r[feature]) for r in features])
        if not np.isfinite(values).all():
            raise ValueError('non-finite raw features')
        for group,mask in [('inside',inside),('outside',~inside)]:
            feature_stats.append(dict(feature=feature,group=group,**summary(values[mask])))
    tables['regional_summary.tsv']=regional; tables['feature_summary.tsv']=feature_stats
    allboot=[]; spearman=[]; allfits=[]; allrepeats=[]; allsummary=[]; selections={}
    for condition,mask in [('all',np.ones(len(i),bool)),('far',~near)]:
        d=distance[mask]/1000; y=C[i[mask],j[mask]]
        boots=bootstrap(n,i[mask],j[mask],d,y,range(4000,6000))
        finite=[r['rho'] for r in boots if r['defined']]; complete=len(finite)==len(boots)
        quantiles=np.quantile(finite,[.025,.975],method='linear') if complete else [None,None]
        point=float(spearmanr(d,y).statistic)
        spearman.append(dict(condition=condition,n_pairs=len(y),rho=point,defined=np.isfinite(point),reason='',n_planned=len(boots),n_finite=len(finite),n_undefined=len(boots)-len(finite),interval_lower=quantiles[0],interval_upper=quantiles[1],median=float(np.median(finite)) if finite else None,interval_method="np.quantile([0.025, 0.975], method='linear')",interval_status='available_all_finite' if complete else 'unavailable_undefined_repeats',undefined_reasons=';'.join(sorted({r['reason'] for r in boots if not r['defined']}))))
        allboot.extend(dict(condition=condition,**r) for r in boots)
        print(condition+' bootstrap complete',flush=True)
        fits,repeats,stats,selection=cross_validate(n,i[mask],j[mask],d,y,folds)
        for dest,rows in [(allfits,fits),(allrepeats,repeats),(allsummary,stats)]:
            dest.extend(dict(condition=condition,**r) for r in rows)
        selections[condition]=selection
    tables.update({'spearman.tsv':spearman,'bootstrap.tsv':allboot,'cv_folds.tsv':allfits,'cv_repeats.tsv':allrepeats,'cv_model_summary.tsv':allsummary})
    validation={}
    for name,rows in tables.items():
        ref=data/'expected'/name
        if ref.exists():
            validation[name]=compare(rows,read_tsv(ref),1e-10 if name.startswith('cv_') else 1e-12)
    validation['similarity_summary.tsv']=compare([r for r in regional if r['phase']=='before'],read_tsv(data/'expected/similarity_summary.tsv'),1e-12)
    expected_selection=json.loads((data/'expected/cv_selection.json').read_text())
    validation['cv_selection.json']={'passed':all(selections[c]['selected_model']==expected_selection[c]['selected_model'] and selections[c]['equivalent_models']==expected_selection[c]['equivalent_models'] and selections[c]['common_seeds']==expected_selection[c]['common_seeds'] for c in selections)}
    displays=display_tables(spearman,allsummary)
    reference_displays=display_tables(read_tsv(data/'expected/spearman.tsv'),read_tsv(data/'expected/cv_model_summary.tsv'))
    validation['display_tables']={'passed':displays==reference_displays}
    tables.update(displays)
    validation['passed']=all(r['passed'] for r in validation.values())
    output.mkdir(parents=True,exist_ok=False)
    for name,rows in tables.items():
        write_tsv(output/name,rows)
    (output/'cv_selection.json').write_text(json.dumps(selections,indent=2)+'\n')
    (output/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    outmanifest={p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in output.iterdir()}
    (output/'manifest.json').write_text(json.dumps(outmanifest,indent=2)+'\n')
    print(json.dumps({'passed':validation['passed'],'output':str(output)}),flush=True)
    return validation['passed']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    raise SystemExit(0 if run(args.data,args.output) else 1)


if __name__=='__main__':
    main()
