# Station Road Network Similarity

This release implements the paper's numerical procedures from saved station indicators, distances and region membership. It does not extract road networks or measure indicators from raw maps. The software uses the MIT License; the data release combines ODbL for the author-controlled numerical database with the original conditions for separately identified third-party inputs. See `LICENSING.md` for the scope.

## Environment and execution

Reference environment: Python 3.12.3 on Linux aarch64, OpenBLAS 0.3.28 (pthreads, neoversen1), with Python package versions in `requirements.txt`. Exact identifiers/ranks and the reported numerical agreement were checked in this reference environment. The requirements file does not fix the BLAS build or CPU: another environment may produce small floating-point differences and near-tied candidate swaps, causing strict verification to fail. Inspect the recorded boundary gaps in the main/sensitivity `verification.json`; do not rewrite expectations to make the check pass. This package does not distribute the original reference container.

Run commands from this directory. Each output directory must be new; existing outputs are preserved.

```sh
python -m pip install -r requirements.txt
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
python -m pytest -c pyproject.toml
python -m paper1.main_analysis --data data/main --output outputs/main
python -m paper1.sensitivity --data data/sensitivity --output outputs/sensitivity
OPENBLAS_NUM_THREADS=8 OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 python -m paper1.regional_distance --data data/regional_distance --output outputs/regional_distance
```

Start the regional/distance process with eight BLAS threads as shown, matching the saved numerical environment. The other modules use one thread. Thread count can change floating-point optimizer results; the fixed environment is part of verification. The BLAS build must support starting eight threads; the regional/distance CLI refuses other pool sizes. Do not increase the BLAS pool size at runtime after starting a one-thread process.

The last command includes station bootstrap and repeated station cross-validation and can take substantially longer than the other commands. An interrupted run's directory is retained: inspect it and choose a new output directory for a justified retry.

## Calculation boundaries

| Module | Calculation inputs and scope |
| --- | --- |
| `main_analysis` | Saved station indicators and quality/selection definitions; feature selection, main scaling and cosine similarities, clipping comparison, dominance and fixed example-pair selection |
| `sensitivity` | Saved indicators, adopted condition-specific fixed centers/scales and station sets; candidate overlap and adopted proximity, park-removal and dominance comparisons |
| `regional_distance` | Saved main similarity matrix, distances, region membership/indicators and sampling/model settings; regional distributions, distance correlation/bootstrap and model cross-validation |

The main module recomputes its scales. Sensitivity comparisons preserve the adopted fixed scales; they do not refit scales after candidate exclusion. The regional/distance module deliberately starts from the saved similarity matrix. Integration verification established exact agreement between that matrix and the main module's recomputation across all 614 × 614 elements (maximum absolute difference 0.0).

Calculation inputs and expected outputs are separate. Expected outputs are used only to check newly calculated results. Fixed scales and fold assignments are scientific inputs where the adopted procedure fixes them. Neither numerical reproduction nor candidate overlap establishes causal effects, spatial independence or overall validity of the method.

Subject sets, feature ordering, tie rules, thresholds and random draws are part of the calculation definition. Main-analysis dominance uses the first feature on an exact maximum tie; the station-specific maximum-feature removal diagnostic requires a unique maximum. These are distinct adopted procedures. Proximity exclusion removes pairs or candidates, not stations, and re-ranking can replenish candidates.

Verification requires exact identifiers/counts and the predetermined continuous tolerances specified in each module. A candidate-identity mismatch is a failure even if similarity differences are tiny. Record swapped similarities or the boundary gap: gaps within the existing continuous tolerance can diagnose near ties, but do not automatically waive a mismatch or authorize changing expected results.

## Data, provenance and updates

See `DATA_AVAILABILITY.md` for origins and source conditions, `manifest.json` for this release's file hashes, and `UPDATING.md` for release maintenance. This release contains no private repository history, correspondence, manuscript drafts or original OSM history. The initial reproduction starts after road measurement; it must not be described as end-to-end reproduction from raw OSM.

See `VERIFICATION.md` for completed checks and their limits. The fixed software release is [paper1-v0.1.0](https://github.com/mopinfish/station-road-network-similarity/releases/tag/paper1-v0.1.0).

## Input organization

All station identifiers are strings; do not convert them to floating-point values or silently reorder arrays independently of their identifiers. TSV headers name the fields, JSON settings fix the relevant station/feature order and scientific constants, and NPY matrices use the recorded order.

| Directory | Files and roles |
| --- | --- |
| `data/main/` | `features_800.tsv`: saved station indicators; `quality.tsv`: inclusion/quality state; `candidate_registry.tsv`: candidate feature definitions; `expected/`: fixed comparison targets |
| `data/sensitivity/` | `features_600.tsv`, `features_800.tsv`, `features_1000.tsv`: range indicators; `park_*.tsv`: park conditions; `settings.json`: fixed condition scales/sets; `distances.tsv`: pair distances; `dominance.tsv`: fixed maximum-component diagnosis checked against reconstructed vectors; `expected/`: comparison targets |
| `data/regional_distance/` | `station_ids.json` and `similarity_main_800.npy`: ordered main matrix; `pair_distance.tsv`: pair distances; `features_raw.tsv`: indicators and regional membership; `cv_station_folds.tsv`: fixed folds; `settings.json`: model/sampling rules; `expected/`: comparison targets |

The regional/distance settings describe the fixed implementation; they are not a general-purpose parameter interface. Changing a settings file alone does not define a new validated study.

Each data directory has a manifest of staged files. Internal export records retain the mapping to source artifacts; the originals are unchanged. Distance conditions use the saved road-origin planar distances in metres. The non-proximity threshold is strictly greater than 1,600 m for the adopted 800 m comparisons and 600–800 m comparison, and greater than 2,000 m for comparisons involving the 1,000 m range. These conservative conditions are not a claim of spatial independence.

## Outputs

Main writes `results.json`, main/Clip NPY matrices and `verification.json`. Sensitivity writes its computed comparison files and `verification.json`. Regional/distance writes TSV summaries, bootstrap and cross-validation rows, `cv_selection.json`, `validation.json` and an output manifest. These files report whether numerical reference checks pass; they do not decide scientific acceptance or authorize publication.

## Research team and affiliation

- **Noboru Otsuka** — research and preparation of the public analysis code.
- **Kayoko Yamamoto** — research collaboration and supervision.

Affiliation: **The University of Electro-Communications (電気通信大学), Japan**.

These research credits are distinct from the software copyright notice. The software copyright holder is Noboru Otsuka; university affiliation does not designate the university as a code copyright holder. See `LICENSE` and `LICENSING.md`.

## Citation

Please use `CITATION.cff` to cite the software. The research team above describes the collaboration; the software citation identifies its code author. The associated paper's final title, authorship and publication details will be added when confirmed. The software repository is https://github.com/mopinfish/station-road-network-similarity. No paper DOI is asserted.

## Saved-input disclosure supplement

`data/supplement/` contains adopted park classifications, area decisions, station group definitions and saved representatives, and the unchanged TMU regional reference layer. `METHODS.md` describes upstream transformations; `SOURCE_NOTICES.md` and `DATA_LICENSE.md` specify the data terms and attribution. These files document existing inputs and decisions; the numerical commands and their saved inputs are unchanged. The executable workflow still starts from saved indicators.
