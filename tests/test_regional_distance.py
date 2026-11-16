import tempfile
import unittest
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from paper1.regional_distance import weighted_rho,rank_groups,fold_masks,folds_for,fit_model,summary,compare,run,cross_validate,display_tables

class RegionalDistanceTests(unittest.TestCase):
    def test_weighted_ties_equal_replication(self):
        x=np.array([1.,1.,2.,3.]); y=np.array([4.,1.,3.,2.]); weights=np.array([1,3,2,0])
        self.assertAlmostEqual(weighted_rho(weights,(rank_groups(x),rank_groups(y))),spearmanr(np.repeat(x,weights),np.repeat(y,weights)).statistic,places=14)

    def test_station_folds_and_boundary(self):
        labels=folds_for(15,3000); i,j=np.triu_indices(15,1)
        train,test=fold_masks(i,j,labels,0)
        self.assertFalse(set(np.r_[i[train],j[train]]) & set(np.r_[i[test],j[test]]))
        self.assertTrue(np.all(labels[i[test]]==labels[j[test]]))
        self.assertEqual((np.array([1599,1600,1601])<=1600).tolist(),[True,True,False])

    def test_linear_fit_and_quantile(self):
        x=np.arange(20,dtype=float); fit=fit_model('linear',x,.4-.01*x)
        self.assertEqual(fit['status'],'ok'); self.assertAlmostEqual(fit['a'],.4,places=7); self.assertAlmostEqual(fit['b'],-.01,places=7)
        self.assertEqual(summary([1,2,4,9])['q1'],1.75)
        self.assertFalse(compare([{'n':2}],[{'n':'3'}],1e-12)['passed'])

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'already exists'):
                run(Path(d),Path(d))

    def test_cv_aggregates_sse_and_display_precision(self):
        n=15; i,j=np.triu_indices(n,1); distance=1+(j-i).astype(float)
        y=.4-.01*distance
        fits,repeats,_,_=cross_validate(n,i,j,distance,y,{3000:folds_for(n,3000)})
        linear=[r for r in fits if r['model']=='linear']
        repeat=next(r for r in repeats if r['model']=='linear')
        self.assertAlmostEqual(repeat['rmse'],np.sqrt(sum(r['sse'] for r in linear)/sum(r['n'] for r in linear)))
        self.assertAlmostEqual(repeat['oos_r2'],1-sum(r['sse'] for r in linear)/sum(r['null_sse'] for r in linear))
        tables=display_tables([dict(condition='all',n_pairs=3,rho=-.21823,interval_lower=-.26434,interval_upper=-.17510)],[dict(condition='all',model='linear',rmse_median=.425413,oos_r2_median=.038709,oos_r2_p2_5=.035165,oos_r2_p97_5=.042109)])
        self.assertEqual(tables['table9.tsv'][0]['rho'],'-0.218')
        self.assertEqual(tables['table10.tsv'][0]['rmse_median'],'0.4254')
        self.assertFalse(compare([{'model':'linear'}],[{'model':'linear','n':'3'}],1e-12)['passed'])

if __name__=='__main__':
    unittest.main()
