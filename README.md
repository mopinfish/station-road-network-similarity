# Station Road Network Similarity

Version `paper1-v0.2.0` extends the v0.1.1 numerical package with measurement from fixed saved road reach/fragments. It reproduces 39 indicators and connects measured 800 m indicators to the existing main analysis. It does not acquire raw OSM or regenerate road extraction. The software uses the MIT License; the data release combines ODbL for the author-controlled numerical database with the original conditions for separately identified third-party inputs. See `LICENSING.md` for the scope.

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
| `road_measurement` | Saved parent-road geometry, fixed origins and reach/fragments; 39 indicators at 600/800/1,000 m |
| `measurement_to_main` | Measured 800 m JSON and separate station mapping; a new main-input directory with unchanged expectations, registry and quality |
| `main_analysis` | Saved station indicators and quality/selection definitions; feature selection, main scaling and cosine similarities, clipping comparison, dominance and fixed example-pair selection |
| `sensitivity` | Saved indicators, adopted condition-specific fixed centers/scales and station sets; candidate overlap and adopted proximity, park-removal and dominance comparisons |
| `regional_distance` | Saved main similarity matrix, distances, region membership/indicators and sampling/model settings; regional distributions, distance correlation/bootstrap and model cross-validation |

The main module recomputes its scales. Sensitivity comparisons preserve the adopted fixed scales; they do not refit scales after candidate exclusion. The regional/distance module deliberately starts from the saved similarity matrix. Integration verification established exact agreement between that matrix and the main module's recomputation across all 614 × 614 elements (maximum absolute difference 0.0).

Calculation inputs and expected outputs are separate. Expected outputs are used only to check newly calculated results. Fixed scales and fold assignments are scientific inputs where the adopted procedure fixes them. Neither numerical reproduction nor candidate overlap establishes causal effects, spatial independence or overall validity of the method.

Subject sets, feature ordering, tie rules, thresholds and random draws are part of the calculation definition. Main-analysis dominance uses the first feature on an exact maximum tie; the station-specific maximum-feature removal diagnostic requires a unique maximum. These are distinct adopted procedures. Proximity exclusion removes pairs or candidates, not stations, and re-ranking can replenish candidates.

Verification requires exact identifiers/counts and the predetermined continuous tolerances specified in each module. A candidate-identity mismatch is a failure even if similarity differences are tiny. Record swapped similarities or the boundary gap: gaps within the existing continuous tolerance can diagnose near ties, but do not automatically waive a mismatch or authorize changing expected results.

## Data, provenance and updates

See `DATA_AVAILABILITY.md` for origins and source conditions, `manifest.json` for this release's file hashes, and `UPDATING.md` for release maintenance. The package contains no private repository history, correspondence, manuscript drafts or original OSM history. The published v0.1.1 baseline starts after road measurement; this extension starts from saved road reach/fragments. Neither is end-to-end reproduction from raw OSM.

See `VERIFICATION.md` for completed checks and their limits. The published baseline is [paper1-v0.1.1](https://github.com/mopinfish/station-road-network-similarity/releases/tag/paper1-v0.1.1). The road-measurement version is [paper1-v0.2.0](https://github.com/mopinfish/station-road-network-similarity/releases/tag/paper1-v0.2.0); its separately distributed road archive is pinned in `road_data.json`.

## Input organization

All station identifiers are strings; do not convert them to floating-point values or silently reorder arrays independently of their identifiers. TSV headers name the fields, JSON settings fix the relevant station/feature order and scientific constants, and NPY matrices use the recorded order.

| Directory | Files and roles |
| --- | --- |
| `data/road_measurement/` | Separate road-ID/station-ID correspondence and offsets under the station provider conditions; road geometry is a separate archive |
| `data/main/` | `features_800.tsv`: saved station indicators; `quality.tsv`: inclusion/quality state; `candidate_registry.tsv`: candidate feature definitions; `expected/`: fixed comparison targets |
| `data/sensitivity/` | `features_600.tsv`, `features_800.tsv`, `features_1000.tsv`: range indicators; `park_*.tsv`: park conditions; `settings.json`: fixed condition scales/sets; `distances.tsv`: pair distances; `dominance.tsv`: fixed maximum-component diagnosis checked against reconstructed vectors; `expected/`: comparison targets |
| `data/regional_distance/` | `station_ids.json` and `similarity_main_800.npy`: ordered main matrix; `pair_distance.tsv`: pair distances; `features_raw.tsv`: indicators and regional membership; `cv_station_folds.tsv`: fixed folds; `settings.json`: model/sampling rules; `expected/`: comparison targets |

The regional/distance settings describe the fixed implementation; they are not a general-purpose parameter interface. Changing a settings file alone does not define a new validated study.

Main, sensitivity, regional/distance and disclosure-supplement datasets have their own manifests. The root manifest lists all selected repository files, including the separate road/station mapping; the road archive has its own manifest. Internal export records retain the mapping to source artifacts; the originals are unchanged. Distance conditions use the saved road-origin planar distances in metres. The non-proximity threshold is strictly greater than 1,600 m for the adopted 800 m comparisons and 600–800 m comparison, and greater than 2,000 m for comparisons involving the 1,000 m range. These conservative conditions are not a claim of spatial independence.

## Outputs

Road measurement writes one JSON per road/radius and an execution record. The adapter writes a new main-input directory; it does not alter the supplied data. Main writes `results.json`, main/Clip NPY matrices and `verification.json`. Sensitivity writes its computed comparison files and `verification.json`. Regional/distance writes TSV summaries, bootstrap and cross-validation rows, `cv_selection.json`, `validation.json` and an output manifest. These files report whether numerical reference checks pass; they do not decide scientific acceptance or authorize publication.

## Research team and affiliation

- **Noboru Otsuka** — research and preparation of the public analysis code.
- **Kayoko Yamamoto** — research collaboration and supervision.

Affiliation: **The University of Electro-Communications (電気通信大学), Japan**.

These research credits are distinct from the software copyright notice. The software copyright holder is Noboru Otsuka; university affiliation does not designate the university as a code copyright holder. See `LICENSE` and `LICENSING.md`.

## Citation

Please use `CITATION.cff` to cite the software. The research team above describes the collaboration; the software citation identifies its code author. The associated paper's final title, authorship and publication details will be added when confirmed. The software repository is https://github.com/mopinfish/station-road-network-similarity. No paper DOI is asserted.

## Saved-input disclosure supplement

`data/supplement/` contains adopted park classifications, area decisions, station group definitions and saved representatives, and the unchanged TMU regional reference layer. `METHODS.md` describes upstream transformations; `SOURCE_NOTICES.md` and `DATA_LICENSE.md` specify the data terms and attribution. These files document existing inputs and decisions; the numerical commands and their saved inputs are unchanged. The v0.1.1 numerical modules start from saved indicators; the separate extension below adds measurement from saved reach/fragments.

## Fixed road-input archive

The version-pinned fetcher uses the `paper1-v0.2.0` Release asset URL, byte count and SHA256 in `road_data.json`. Input packaging, local archive retrieval, full road measurement and downstream numerical verification are complete. Retrieve the fixed archive with:

```sh
python -m paper1.fetch_roads --output road_inputs
```

Alternatively, use an already downloaded archive matching `road_data.json` (choose one retrieval method; both create a new destination):

```sh
python -m paper1.fetch_roads --archive /path/to/road_measurement_v1.tar.gz --output road_inputs
```

The command verifies the archive and every listed member before creating a new destination; it refuses to overwrite an existing dataset. The large road package stays outside Git history. It contains saved reach/fragments, road geometry and road origins under ODbL 1.0. The separately licensed station correspondence is `data/road_measurement/station_map.tsv`; it is not part of the road archive. The immutable archive retains its dated preparation notices; current release identification and retrieval settings are in this repository and `road_data.json`.

The intended measurement start is saved reach/fragments. Road acquisition, simplification, origin selection and reach extraction remain in the saved-input preparation; this extension does not claim to execute them. The computed indicators reproduce the adopted results; no new road condition or station population is introduced.

### Complete saved-road measurement chain verified locally

The `paper1.road_measurement` module restores measured multigraphs from saved road reach/fragments and computes the adopted 39 indicators. All 615 fixed road records at 600, 800 and 1,000 m (71,955 cells, including missingness) match exactly as parsed numeric values. Missing reasons and graph invariants also match. The newly measured 800 m indicators pass the unchanged main-analysis Gate D (1e-12 numerical tolerances and exact ordered top-5/10/20 candidates for main and Clip). The 611-station selection population, 614-station fit/main population, fixed eight features and 43 affected Clip station IDs are preserved. The 600/1,000 m input and range-specific fit checks also pass; other sensitivity analyses were not rerun. These are the recorded pre-release numerical checks. The command below is a small explicit subset.

```sh
mkdir -p outputs
python -m paper1.road_measurement --roads road_inputs --output outputs/pilot --road-ids r000001 r000007 r000336
```

The output parent directory must exist and the output directory must be new. Road IDs are joined to stations only through the separate correspondence table. The calculation does not read expected indicator values.

### All 615 records and connection to main analysis

The commands below are separate public steps. They do not depend on the private concurrent supervisor. Measuring all records sequentially can take hours; do not repeat an existing run merely to change worker settings. Use a new output directory and preserve completed outputs.

```sh
mkdir -p outputs
python - <<'PYCODE'
import csv
import subprocess
import sys
with open('data/road_measurement/station_map.tsv', newline='') as stream:
    road_ids = [row['road_id'] for row in csv.DictReader(stream, delimiter='\t')]
assert len(road_ids) == 615 and len(set(road_ids)) == 615
subprocess.run([sys.executable, '-m', 'paper1.road_measurement',
                '--roads', 'road_inputs', '--output', 'outputs/roads_all',
                '--road-ids', *road_ids], check=True)
PYCODE
python -m paper1.measurement_to_main --measurements outputs/roads_all --station-map data/road_measurement/station_map.tsv --data data/main --output outputs/main_measured_inputs
python -m paper1.main_analysis --data outputs/main_measured_inputs --output outputs/main_measured_results
```

The adapter reads only the 800 m measurement JSON values for the new table, joins them through the separate station map and renders missing values as blank TSV cells. It copies the fixed main input directory to a new location, replaces only `features_800.tsv`, and updates that file's manifest hash. Expected values, the candidate registry, quality ledger and all other manifest pins remain unchanged. The final command runs the original numerical and exact-ranking checks against those unchanged expectations. Existing destinations and incomplete or inconsistent mappings/measurements are rejected. This connection does not rerun the other sensitivity or regional/distance modules automatically.
