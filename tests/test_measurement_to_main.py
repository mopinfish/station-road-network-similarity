import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from paper1.measurement_to_main import prepare


class MeasurementToMainTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.data=self.root/'data';self.data.mkdir()
        (self.data/'expected').mkdir();self.measured=self.root/'measured';self.measured.mkdir()
        self.mapping=self.root/'station_map.tsv';self.features=[f'f{i:02}' for i in range(39)]
        self.rows=[{'road_id':f'r{i:06}','g_cd':str(2000000+614-i)} for i in range(615)]
        self.write_map(self.rows)
        (self.data/'quality.tsv').write_text('g_cd\n'+''.join(r['g_cd']+'\n' for r in self.rows))
        (self.data/'candidate_registry.tsv').write_text('feature\n'+'\n'.join(self.features)+'\n')
        (self.data/'features_800.tsv').write_text('saved indicators must not supply measured values\n')
        (self.data/'expected/results.json').write_text('expected bytes are copied, never used for generation\n')
        self.files={str(p.relative_to(self.data)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.data.rglob('*') if p.is_file()}
        (self.data/'manifest.json').write_text(json.dumps({'files':self.files,'records':{'features':615}}))
        for i,r in enumerate(self.rows):
            values={f:i+j/100 for j,f in enumerate(self.features)}
            if i==0:values['f38']=None
            (self.measured/f"{r['road_id']}_800.json").write_text(json.dumps({'road_id':r['road_id'],'radius_m':800,'values':values}))
    def write_map(self,rows):
        with self.mapping.open('w') as f:
            w=csv.DictWriter(f,fieldnames=['road_id','g_cd'],delimiter='\t');w.writeheader();w.writerows(rows)
    def test_join_null_and_unchanged_reference_bytes(self):
        out=self.root/'out';prepare(self.measured,self.mapping,self.data,out)
        with (out/'features_800.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
        self.assertEqual(len(rows),615);self.assertEqual(list(rows[0]),['g_cd']+self.features)
        self.assertEqual(rows[0]['g_cd'],'2000000');self.assertEqual(float(rows[0]['f00']),614)
        self.assertEqual(rows[-1]['f38'],'')
        manifest=json.loads((out/'manifest.json').read_text())
        for name,pin in self.files.items():
            self.assertEqual(hashlib.sha256((self.data/name).read_bytes()).hexdigest(),pin)
            if name!='features_800.tsv':
                self.assertEqual((out/name).read_bytes(),(self.data/name).read_bytes())
                self.assertEqual(manifest['files'][name],pin)
        self.assertEqual(manifest['files']['features_800.tsv'],hashlib.sha256((out/'features_800.tsv').read_bytes()).hexdigest())
    def test_reject_incomplete_duplicate_and_existing_output(self):
        out=self.root/'out'
        self.write_map(self.rows[:-1]+[self.rows[0]])
        with self.assertRaises(ValueError):prepare(self.measured,self.mapping,self.data,out)
        self.assertFalse(out.exists());self.write_map(self.rows)
        missing=self.measured/'r000614_800.json';saved=missing.read_bytes();missing.unlink()
        with self.assertRaises(FileNotFoundError):prepare(self.measured,self.mapping,self.data,out)
        self.assertFalse(out.exists());missing.write_bytes(saved)
        wrong=json.loads(saved);wrong['radius_m']=600;missing.write_text(json.dumps(wrong))
        with self.assertRaises(ValueError):prepare(self.measured,self.mapping,self.data,out)
        self.assertFalse(out.exists());missing.write_bytes(saved)
        out.mkdir()
        with self.assertRaises(FileExistsError):prepare(self.measured,self.mapping,self.data,out)

if __name__=='__main__':unittest.main()
