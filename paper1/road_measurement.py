"""Measure saved road reach/fragments; do not generate roads or read expected values."""
from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
import time

import networkx as nx
import osmnx as ox
from shapely.geometry import LineString, MultiPoint
from shapely.ops import substring

FEATURES = (
    'n_nodes', 'e_edges', 'p_components', 'circuit_index_mu', 'mean_circuit_index_mu_a',
    'alpha_index', 'beta_index', 'gamma_index', 'avg_shortest_path_Di', 'total_edge_length_L',
    'road_density_Dl_m_per_ha', 'intersection_count_deg≥3', 'intersection_density_Dc_per_ha',
    'avg_circuity_A', 'area_m2', 'degree_centrality_mean', 'degree_centrality_std',
    'closeness_centrality_mean', 'closeness_centrality_std', 'betweenness_centrality_mean',
    'betweenness_centrality_std', 'basic_n', 'basic_m', 'basic_k_avg', 'basic_edge_length_total',
    'basic_edge_length_avg', 'basic_streets_per_node_avg', 'basic_intersection_count',
    'basic_street_length_total', 'basic_street_segment_count', 'basic_street_length_avg',
    'basic_circuity_avg', 'basic_self_loop_proportion', 'basic_clean_intersection_count',
    'basic_node_density_km', 'basic_intersection_density_km', 'basic_edge_density_km',
    'basic_street_density_km', 'basic_clean_intersection_density_km')
ORIGIN = ('origin',)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def restore(structure, origin, radius):
    """Reconstruct pre-cut and measured multigraphs from the supplied saved intervals."""
    require(radius in (600, 800, 1000), 'unsupported radius')
    require(origin['status'] == 'ok', 'undefined road origin')
    parents = {s['segment_id']: s for s in structure['segments']}
    require(len(parents) == len(structure['segments']), 'duplicate parent')
    pre = nx.MultiGraph(crs='EPSG:32654')
    xy = {}
    for s in parents.values():
        require(len(s['coords']) == len(s['path']), 'parent path/geometry mismatch')
        for n, point in zip(s['path'], s['coords']):
            point = tuple(point)
            require(n not in xy or xy[n] == point, 'conflicting node coordinates')
            xy[n] = point
        for n in (s['u'], s['v']): pre.add_node(n, x=xy[n][0], y=xy[n][1])
        pre.add_edge(s['u'], s['v'], key=s['segment_id'], segment_id=s['segment_id'], length=s['length_m'])
    measured = nx.MultiGraph(crs='EPSG:32654')
    # Preserve the saved real-node order, not a new sort order.
    for row in structure['reached_nodes']:
        if row['dist_m'] <= radius:
            n = row['id']
            require(n in pre and xy[n] == (row['x'], row['y']), 'invalid reached node')
            require(n not in measured, 'duplicate reached node')
            measured.add_node(n, x=row['x'], y=row['y'], kind='real', dist_m=row['dist_m'])
    if origin['kind'] == 'existing_node':
        require(origin['node'] in measured and tuple(origin['xy']) == xy[origin['node']], 'invalid node origin')
    else:
        require(origin['kind'] == 'edge_interior' and origin['segment_id'] in parents, 'invalid interior origin')
        s = parents[origin['segment_id']]
        require(0 < origin['position_m'] < s['length_m'], 'origin outside parent interior')
        measured.add_node(ORIGIN, x=origin['xy'][0], y=origin['xy'][1], kind='origin', dist_m=0.)
    reaches = structure['reach'][str(radius)]
    require(set(reaches) <= set(parents), 'missing reach parent')

    def endpoint(s, position, is_start):
        sid = s['segment_id']
        if s['length_m'] == 0:
            node = s['u'] if is_start else s['v']
        elif origin['kind'] == 'edge_interior' and sid == origin['segment_id'] and position == origin['position_m']:
            node = ORIGIN
        elif position == 0:
            node = s['u']
        elif position == s['length_m']:
            node = s['v']
        else:
            node = ('boundary', sid, position)
            if node not in measured:
                point = LineString(s['coords']).interpolate(position)
                measured.add_node(node, x=float(point.x), y=float(point.y), kind='boundary', dist_m=float(radius))
        require(node in measured, 'fragment endpoint is not a reached node')
        return node

    for f in structure['fragments'][str(radius)]:
        sid = f['segment_id']
        require(sid in parents and sid in reaches, 'missing fragment parent/reach')
        s = parents[sid]; a, b = f['start_m'], f['end_m']
        require(0 <= a <= b <= s['length_m'] and f['length_m'] == b-a, 'invalid fragment interval/length')
        require(any(lo <= a and b <= hi for lo, hi in reaches[sid]['intervals']), 'fragment outside saved reach')
        require(b > a or s['is_zero_length'], 'touch-only fragment must not create edge')
        u, v = endpoint(s, a, True), endpoint(s, b, False)
        line = LineString(s['coords'])
        geometry = line if s['is_zero_length'] else substring(line, a, b)
        measured.add_edge(u, v, segment_id=sid, start_m=a, end_m=b, length=f['length_m'], geometry=geometry)
    return {'measurement': measured, 'pre': pre, 'parents': parents, 'reach': reaches,
            'xy': xy, 'radius': radius, 'origin': origin}


def auxiliary(measured):
    graph = measured.copy()
    boundaries = [n for n, d in graph.nodes(data=True) if d['kind'] == 'boundary']
    require(all(graph.degree(n) == 1 for n in boundaries), 'boundary must be a leaf')
    graph.remove_nodes_from(boundaries)
    if ORIGIN in graph:
        incident = list(graph.edges(ORIGIN, keys=True, data=True))
        require(len(incident) <= 2, 'origin has too many incident edges')
        if len(incident) == 2:
            a, b = incident
            require(a[1] != ORIGIN and b[1] != ORIGIN and a[3]['segment_id'] == b[3]['segment_id'],
                    'origin fragments disagree')
            graph.add_edge(a[1], b[1], segment_id=a[3]['segment_id'], length=a[3]['length']+b[3]['length'])
        graph.remove_node(ORIGIN)
    return graph


def measure(restored):
    """Compute the adopted 39 columns and exact undefined-reason labels."""
    gm = restored['measurement']; graph = auxiliary(gm); xy = restored['xy']
    n, edges = graph.number_of_nodes(), graph.number_of_edges()
    components = nx.number_connected_components(graph) if n else 0
    pm = nx.number_connected_components(gm) if len(gm) else 0
    cycle = gm.number_of_edges()-len(gm)+pm
    complete = [restored['parents'][sid] for sid, r in restored['reach'].items() if r['status'] == 'complete']
    real = {node for node, d in gm.nodes(data=True) if d['kind'] == 'real'}
    require(set(graph) == real, 'auxiliary nodes differ from real reached nodes')
    require(components == (1 if n else 0), 'invalid auxiliary component count')
    require(cycle == edges-n+components, 'cycle rank changed during suppression')
    require(len(complete) == edges, 'complete-parent/auxiliary-edge count differs')
    points = [(d['x'], d['y']) for _, d in gm.nodes(data=True)]
    for _, _, d in gm.edges(data=True): points.extend(tuple(c[:2]) for c in d['geometry'].coords)
    area = float(MultiPoint(points).convex_hull.area) if points else 0.
    length = float(sum(d['length'] for _, _, d in gm.edges(data=True)))
    sc_all = ox.stats.count_streets_per_node(restored['pre'].to_directed())
    streets = {node:int(sc_all[node]) for node in graph}
    ge2, ge3 = sum(c >= 2 for c in streets.values()), sum(c >= 3 for c in streets.values())
    zero = sum(d['length'] == 0. for _, _, d in graph.edges(data=True))
    values = {'n_nodes':n,'e_edges':edges,'p_components':components,'circuit_index_mu':cycle,
              'total_edge_length_L':length,'area_m2':area,'intersection_count_deg≥3':ge3,
              'basic_intersection_count':ge2}
    missing = {}

    def emit(name, value, reason=None):
        values[name] = None if reason else value
        if reason: missing[name] = reason

    emit('alpha_index', (edges-n+components)/(2*n-5) if n >= 3 else None, None if n >= 3 else 'small_n')
    emit('gamma_index', edges/(3*(n-2)) if n >= 3 else None, None if n >= 3 else 'small_n')
    emit('beta_index', edges/n if n else None, None if n else 'small_n')
    emit('basic_streets_per_node_avg', sum(streets.values())/n if n else None, None if n else 'small_n')
    if n >= 2:
        total, count, ratios = 0, 0, []
        for u, targets in nx.all_pairs_dijkstra_path_length(graph, weight='length'):
            for v, distance in targets.items():
                if u != v:
                    total += distance; count += 1
                    straight = math.dist(xy[u], xy[v])
                    if straight > 0: ratios.append(distance/straight)
        emit('avg_shortest_path_Di', total/count if count else None, None if count else 'no_pair')
        emit('avg_circuity_A', sum(ratios)/len(ratios) if ratios else None, None if ratios else 'no_pair')
    else:
        for name in ('avg_shortest_path_Di','avg_circuity_A'): emit(name,None,'small_n')
    for label, calculate in (
        ('degree', lambda: nx.degree_centrality(graph)),
        ('closeness', lambda: nx.closeness_centrality(graph, distance='length', wf_improved=True)),
        ('betweenness', lambda: nx.betweenness_centrality(graph, weight='length', normalized=True, endpoints=False))):
        reason = 'small_n' if n < (3 if label == 'betweenness' else 2) else (
                 'zero_length_edge' if label == 'betweenness' and zero else None)
        sample = list(calculate().values()) if reason is None else None
        emit(label+'_centrality_mean', statistics.mean(sample) if sample is not None else None, reason)
        emit(label+'_centrality_std', statistics.stdev(sample) if sample is not None else None, reason)
    c = len(complete)
    complete_length = sum(s['length_m'] for s in complete)
    straight_length = sum(math.dist(xy[s['u']],xy[s['v']]) for s in complete)
    emit('basic_street_length_avg', complete_length/c if c else None, None if c else 'no_complete_segment')
    emit('basic_circuity_avg', complete_length/straight_length if c and straight_length > 0 else None,
         'no_complete_segment' if not c else 'zero_straight_sum' if straight_length <= 0 else None)
    emit('basic_self_loop_proportion', sum(s['is_self_loop'] for s in complete)/c if c else None,
         None if c else 'no_complete_segment')
    clean_graph = nx.MultiDiGraph(crs='EPSG:32654')
    for node, count in streets.items():
        if count >= 2: clean_graph.add_node(node, x=float(xy[node][0]), y=float(xy[node][1]), street_count=count)
    clean = int(len(ox.simplification.consolidate_intersections(clean_graph, tolerance=15., rebuild_graph=False,
                  dead_ends=False))) if len(clean_graph) else 0
    values['basic_clean_intersection_count'] = clean
    for name, numerator, unit in (
        ('mean_circuit_index_mu_a',cycle,1e4), ('road_density_Dl_m_per_ha',length,1e4),
        ('intersection_density_Dc_per_ha',ge3,1e4), ('basic_node_density_km',n,1e6),
        ('basic_intersection_density_km',ge2,1e6), ('basic_clean_intersection_density_km',clean,1e6)):
        emit(name, numerator/(area/unit) if area > 0 else None, None if area > 0 else 'zero_area')
    for name, source, factor in (
        ('basic_n','n_nodes',1), ('basic_m','e_edges',1), ('basic_k_avg','beta_index',2.),
        ('basic_edge_length_total','total_edge_length_L',1), ('basic_edge_length_avg','basic_street_length_avg',1),
        ('basic_street_length_total','total_edge_length_L',1), ('basic_street_segment_count','e_edges',1),
        ('basic_edge_density_km','road_density_Dl_m_per_ha',100.), ('basic_street_density_km','road_density_Dl_m_per_ha',100.)):
        emit(name, values[source]*factor if source not in missing else None, missing.get(source))
    require(all(x is None or math.isfinite(x) for x in values.values()), 'nonfinite measured value')
    return {'values':{f:values[f] for f in FEATURES}, 'missing':{f:missing[f] for f in FEATURES if f in missing},
            'invariants':{'n_meas':len(gm),'e_meas':gm.number_of_edges(),'n_aux':n,'e_aux':edges,
                          'p_aux':components,'mu_meas':cycle,'mu_aux':edges-n+components,'complete_parents':c,
                          'zero_length_edges_aux':zero,'definition_version':'m215v1'}}


def file_hash(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roads',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--road-ids',nargs='+',required=True,help='Explicit fixed road IDs to measure')
    args = parser.parse_args()
    roads, output = Path(args.roads), Path(args.output)
    require(not output.exists(), 'measurement output already exists')
    manifest=json.loads((roads/'manifest.json').read_text()); origins=json.loads((roads/'origins.json').read_text())
    require(len(set(args.road_ids)) == len(args.road_ids) and set(args.road_ids) <= set(origins),'unknown/duplicate road IDs')
    for name in ('origins.json','definition.json'):
        require(file_hash(roads/name)==manifest['files'][name]['sha256'],'input metadata hash mismatch')
    definition=json.loads((roads/'definition.json').read_text())
    require(definition['features_old_order']==list(FEATURES) and definition['radii_m']==[600,800,1000], 'definition differs')
    output.mkdir(); execution={'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'running','module_sha256':file_hash(__file__),'road_manifest_sha256':file_hash(roads/'manifest.json'),
                              'road_ids':args.road_ids,'radii_m':[600,800,1000],'results':[]}
    for rid in args.road_ids:
        source=roads/'groups'/f'{rid}.structure.json.gz'
        require(file_hash(source)==manifest['files'][f'groups/{rid}.structure.json.gz']['sha256'],'structure hash mismatch')
        data=json.loads(gzip.decompress(source.read_bytes()))
        for radius in (600,800,1000):
            started=time.perf_counter(); result=measure(restore(data,origins[rid],radius))
            record={'road_id':rid,'radius_m':radius,**result}
            path=output/f'{rid}_{radius}.json';path.write_text(json.dumps(record,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
            elapsed=time.perf_counter()-started
            execution['results'].append({'road_id':rid,'radius_m':radius,'elapsed_s':elapsed,'sha256':file_hash(path)})
            (output/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')
            print(json.dumps({'road_id':rid,'radius_m':radius,'elapsed_s':elapsed}),flush=True)
    execution['status']='complete'; execution['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    (output/'execution.json').write_text(json.dumps(execution,indent=2)+'\n')


if __name__=='__main__': main()
