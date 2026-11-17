"""Join fixed 800 m road measurements into a new main-analysis input directory."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def table(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream,delimiter='\t'))


def prepare(measurements,station_map,data,output):
    measurements,data,output=map(Path,(measurements,data,output))
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    manifest=json.loads((data/'manifest.json').read_text())
    for name,pin in manifest['files'].items():
        if digest(data/name)!=pin:
            raise ValueError('baseline input hash mismatch: '+name)
    features=[row['feature'] for row in table(data/'candidate_registry.tsv')]
    mapping=table(station_map);quality=table(data/'quality.tsv')
    ids=[r['g_cd'] for r in mapping];road_ids=[r['road_id'] for r in mapping]
    if len(features)!=39 or len(set(features))!=39:
        raise ValueError('39 distinct indicator columns required')
    if len(mapping)!=615 or len(set(ids))!=615 or len(set(road_ids))!=615 or set(ids)!={r['g_cd'] for r in quality}:
        raise ValueError('fixed 615-group mapping/quality population differs')
    rows=[]
    for row in sorted(mapping,key=lambda r:r['g_cd']):
        rid=row['road_id'];record=json.loads((measurements/f'{rid}_800.json').read_text())
        if record.get('road_id')!=rid or record.get('radius_m')!=800:
            raise ValueError('road/radius identity mismatch: '+rid)
        values=record['values']
        if set(values)!=set(features):
            raise ValueError('measured indicator columns differ: '+rid)
        if any(v is not None and (isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v)) for v in values.values()):
            raise ValueError('nonfinite/non-numeric measurement: '+rid)
        rows.append({'g_cd':row['g_cd'],**{f:values[f] for f in features}})
    # Expected values are never parsed or used to generate measured rows.
    shutil.copytree(data,output)
    with (output/'features_800.tsv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['g_cd']+features,delimiter='\t',lineterminator='\n')
        writer.writeheader();writer.writerows(rows)
    manifest['files']['features_800.tsv']=digest(output/'features_800.tsv')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return {'records':len(rows),'features':len(features),'output':str(output),'expectations_unchanged':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurements',required=True)
    parser.add_argument('--station-map',required=True)
    parser.add_argument('--data',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    print(json.dumps(prepare(args.measurements,args.station_map,args.data,args.output),indent=2))


if __name__=='__main__':main()
