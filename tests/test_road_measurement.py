"""Hand-sized road ledgers test the measurement contract without private code."""
import copy
import math

import pytest


def segment(sid, u, v, coords, path=None):
    return {'segment_id':sid,'u':u,'v':v,'coords':coords,
            'path':path or [u,v], 'way_ids':[101],
            'length_m':sum(math.dist(a,b) for a,b in zip(coords,coords[1:])),
            'is_self_loop':u==v,'is_ring':False,
            'is_zero_length':all(a==b for a,b in zip(coords,coords[1:]))}


def ledger(nodes, segments, reach=None, fragments=None):
    if reach is None:
        reach={s['segment_id']:{'status':'complete','intervals':[[0.,s['length_m']]]} for s in segments}
    if fragments is None:
        fragments=[{'segment_id':s['segment_id'],'start_m':0.,'end_m':s['length_m'],'length_m':s['length_m']} for s in segments]
    return {'reached_nodes_radius_m':1000,'reached_nodes':nodes,'segments':segments,
            'reach':{'600':reach},'fragments':{'600':fragments}}


def node(n,x,y,d): return {'id':n,'x':x,'y':y,'dist_m':d}


def existing(n,xy):
    return {'status':'ok','kind':'existing_node','node':n,'segment_id':None,'position_m':None,'xy':xy}


def square():
    nodes=[node(1,0.,0.,0.),node(2,100.,0.,100.),node(3,100.,100.,200.),node(4,0.,100.,100.)]
    edges=[segment('1-2-0',1,2,[[0.,0.],[100.,0.]]),segment('2-3-0',2,3,[[100.,0.],[100.,100.]]),
           segment('3-4-0',3,4,[[100.,100.],[0.,100.]]),segment('4-1-0',4,1,[[0.,100.],[0.,0.]])]
    return ledger(nodes,edges),existing(1,[0.,0.])


def run(data,origin):
    from paper1.road_measurement import restore, measure
    restored=restore(data,origin,600)
    return restored,measure(restored)


def test_square_all_families_have_hand_calculated_values():
    _, result=run(*square());v=result['values']
    expected={'n_nodes':4,'e_edges':4,'p_components':1,'circuit_index_mu':1,
       'mean_circuit_index_mu_a':1.,'alpha_index':1/3,'beta_index':1.,'gamma_index':2/3,
       'avg_shortest_path_Di':400/3,'total_edge_length_L':400.,'road_density_Dl_m_per_ha':400.,
       'intersection_count_deg≥3':0,'intersection_density_Dc_per_ha':0.,'avg_circuity_A':(2+math.sqrt(2))/3,
       'area_m2':10000.,'degree_centrality_mean':2/3,'degree_centrality_std':0.,
       'closeness_centrality_mean':3/400,'closeness_centrality_std':0.,
       'betweenness_centrality_mean':1/6,'betweenness_centrality_std':0.,
       'basic_n':4,'basic_m':4,'basic_k_avg':2.,'basic_edge_length_total':400.,
       'basic_edge_length_avg':100.,'basic_streets_per_node_avg':2.,'basic_intersection_count':4,
       'basic_street_length_total':400.,'basic_street_segment_count':4,'basic_street_length_avg':100.,
       'basic_circuity_avg':1.,'basic_self_loop_proportion':0.,'basic_clean_intersection_count':4,
       'basic_node_density_km':400.,'basic_intersection_density_km':400.,
       'basic_edge_density_km':40000.,'basic_street_density_km':40000.,'basic_clean_intersection_density_km':400.}
    assert set(v)==set(expected) and result['missing']=={}
    for key,value in expected.items():assert v[key]==pytest.approx(value,rel=1e-9,abs=1e-9),key


def test_hull_includes_bent_edge_interior_coordinates():
    d,o=square();s=d['segments'][0];s.update(coords=[[0.,0.],[50.,-50.],[100.,0.]],path=[1,99,2],length_m=math.sqrt(20000))
    d['reach']['600']['1-2-0']['intervals']=[[0.,s['length_m']]]
    d['fragments']['600'][0].update(end_m=s['length_m'],length_m=s['length_m'])
    _,r=run(d,o)
    assert r['values']['area_m2']==12500.
    assert r['values']['total_edge_length_L']==pytest.approx(300+math.sqrt(20000))


def test_interior_origin_split_is_suppressed_without_losing_parent():
    d,_=square()
    for n in d['reached_nodes']:n['dist_m']={1:50.,2:50.,3:150.,4:150.}[n['id']]
    d['fragments']['600'][:1]=[{'segment_id':'1-2-0','start_m':0.,'end_m':50.,'length_m':50.},
                              {'segment_id':'1-2-0','start_m':50.,'end_m':100.,'length_m':50.}]
    o={'status':'ok','kind':'edge_interior','node':None,'segment_id':'1-2-0','position_m':50.,'xy':[50.,0.]}
    restored,r=run(d,o)
    assert restored['measurement'].number_of_nodes()==5
    assert r['invariants']['n_aux']==4 and r['invariants']['e_aux']==4
    assert r['values']['total_edge_length_L']==400.


def test_two_sided_gap_keeps_separate_boundary_leaves():
    ss=[segment('1-2-0',1,2,[[0.,0.],[100.,0.]]),segment('1-3-0',1,3,[[0.,0.],[0.,100.]]),
        segment('2-3-0',2,3,[[100.,0.],[800.,0.],[800.,100.],[0.,100.]],path=[2,8,9,3])]
    d=ledger([node(1,0,0,0),node(2,100,0,100),node(3,0,100,100)],ss)
    d['reach']['600']['2-3-0']={'status':'two_sided_gap','intervals':[[0.,500.],[1100.,1600.]]}
    d['fragments']['600'][2:]=[{'segment_id':'2-3-0','start_m':0.,'end_m':500.,'length_m':500.},
                              {'segment_id':'2-3-0','start_m':1100.,'end_m':1600.,'length_m':500.}]
    restored,r=run(d,existing(1,[0.,0.]))
    assert restored['measurement'].number_of_edges()==4
    assert r['invariants']['e_aux']==2 and r['values']['circuit_index_mu']==0
    assert r['values']['total_edge_length_L']==1200.
    assert r['values']['basic_street_length_avg']==100.


def test_parallel_edges_and_multiple_loops_keep_street_count_definition():
    ss=[segment('1-2-0',1,2,[[0.,0.],[100.,0.]]),segment('1-2-1',1,2,[[0.,0.],[100.,0.]]),
        segment('1-1-0',1,1,[[0.,0.],[0.,50.],[50.,0.],[0.,0.]],path=[1,8,9,1]),
        segment('1-1-1',1,1,[[0.,0.],[0.,-50.],[-50.,0.],[0.,0.]],path=[1,10,11,1])]
    _,r=run(ledger([node(1,0,0,0),node(2,100,0,100)],ss),existing(1,[0.,0.]))
    assert r['values']['e_edges']==4
    assert r['values']['basic_self_loop_proportion']==.5
    assert r['values']['basic_streets_per_node_avg']==3. # two parallel streets; all loops count as two at node 1


def test_zero_length_edge_and_zero_area_keep_missing_reasons():
    ss=[segment('1-2-0',1,2,[[0.,0.],[0.,0.]]),segment('2-3-0',2,3,[[0.,0.],[100.,0.]])]
    _,r=run(ledger([node(1,0,0,0),node(2,0,0,0),node(3,100,0,100)],ss),existing(1,[0.,0.]))
    assert r['values']['e_edges']==2 and r['values']['avg_circuity_A']==1.
    assert r['missing']['betweenness_centrality_mean']=='zero_length_edge'
    assert r['missing']['road_density_Dl_m_per_ha']=='zero_area'
    assert r['values']['road_density_Dl_m_per_ha'] is None


def test_exact_radius_touch_adds_no_edge_but_counts_parent_street():
    ss=[segment('1-2-0',1,2,[[0.,0.],[600.,0.]]),segment('2-3-0',2,3,[[600.,0.],[700.,0.]])]
    d=ledger([node(1,0,0,0),node(2,600,0,600),node(3,700,0,700)],ss)
    d['reach']['600']['2-3-0']={'status':'touch_only','intervals':[[0.,0.]]};d['fragments']['600'].pop()
    restored,r=run(d,existing(1,[0.,0.]))
    assert restored['measurement'].number_of_edges()==1
    assert r['values']['basic_streets_per_node_avg']==1.5
    assert r['values']['n_nodes']==2


def test_no_reached_real_node_preserves_small_n_and_no_complete_parent():
    ss=[segment('1-2-0',1,2,[[0.,0.],[2000.,0.]])]
    d=ledger([node(1,0,0,1000),node(2,2000,0,1000)],ss,
       {'1-2-0':{'status':'partial','intervals':[[400.,1600.]]}},
       [{'segment_id':'1-2-0','start_m':400.,'end_m':1000.,'length_m':600.},
        {'segment_id':'1-2-0','start_m':1000.,'end_m':1600.,'length_m':600.}])
    _,r=run(d,{'status':'ok','kind':'edge_interior','node':None,'segment_id':'1-2-0','position_m':1000.,'xy':[1000.,0.]})
    assert r['values']['n_nodes']==0 and r['values']['p_components']==0
    assert r['values']['total_edge_length_L']==1200.
    assert r['missing']['avg_shortest_path_Di']=='small_n'
    assert r['missing']['basic_street_length_avg']=='no_complete_segment'


@pytest.mark.parametrize('fault',['parent','origin'])
def test_invalid_references_stop_instead_of_silent_substitution(fault):
    from paper1.road_measurement import restore
    d,o=square()
    if fault=='parent':d['fragments']['600'][0]['segment_id']='unknown'
    else:o['node']=999
    with pytest.raises(ValueError):restore(d,o,600)
