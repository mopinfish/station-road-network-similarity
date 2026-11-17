# Verification record

Published v0.1.1 baseline verification date: 2026-11-16. The table below records the baseline checks; the subsequent saved-road extension and its 41-test suite are recorded in the later sections. This records numerical reproduction, not publication approval or validation of every scientific interpretation. Reference environment details are in `environment.json`; other CPUs/BLAS builds are not verified.

| Scope | Result |
| --- | --- |
| Published v0.1.1 baseline test suite | 18 tests passed, no skips/deselections |
| Main analysis | Selection populations 611/614; selected features/order, scales, vectors, dominance, Clip comparisons and fixed six pairs match. Main 614 × 614 similarity matrix maximum difference 0.0. Ordered top-5/10/20 candidates match exactly. |
| Sensitivity | 395,775 checks passed, including 31,912 saved ordered candidate lists and 119 display cells in adopted tables 6–8 |
| Regional/distance | Regional and indicator distributions, Spearman and 4,000 bootstrap rows match exactly; 800 fold fits, 160 repeat rows and 8 model summaries match exactly in the adopted eight-thread fitting environment; table 9/10 display values match |
| Cross-module boundary | Recomputed main matrix equals the regional/distance input matrix, all 614 × 614 elements |

Each module was exercised from an independent temporary tree containing only its code and declared data. No private analysis module or manuscript was required at runtime. Inputs/expected outputs were kept separate, and original source files were preserved.

An initial one-thread regional/distance run matched regional, correlation and all bootstrap values but failed the fixed tolerances for some linear-fit fields. A targeted startup-eight-thread CV reconciliation reproduced every CV field exactly. Finally, the documented full regional/distance CLI was executed from the separate local candidate directory with eight startup threads and an empty PYTHONPATH: it completed in about 330 seconds with exit code 0 and all reference checks passing. This final run covers both complete bootstrap conditions and all CV fits in a single invocation. Earlier failed runs remain in the private maintenance record; expected values and tolerances were not changed.

Independent Codex checks include separate reconstruction of main selection and candidates, and 2,452 station-comparison rows for Clip and the 600–800 m range comparison. Independent Codex accepted all three implementations with no unresolved major findings; Claude approved the final code/document review after the environment explanation was clarified. Their detailed records remain in the private maintenance report. The public candidate excludes internal review conversations and private source paths.

For the original v0.1.1 checks above, upstream road extraction/measurement, alternative environments, public download/retrieval and publication were outside scope. The subsequent local fixed-road measurement checks are recorded below; new acquisition/extraction and alternative environments remain outside scope. The private research repository's entire test suite was not rerun because its production code/configuration was unchanged. Future updates must test the affected scientific rules and paper settings as described in `UPDATING.md`.

The later disclosure supplement was checked independently against saved sources: 1,545 classification rows, 615 station-group rows, five area decisions and two retained references, and the unchanged 69-feature regional layer. Existing numerical inputs and source/test code retain their previously verified hashes. The supplement adds provenance and input disclosure only; numerical analysis was not rerun for these document/data-transcription changes.

## Fixed-road extension: historical input-preparation stage

The extension was prepared from the 81 selected files of the released baseline. The new fetcher passed 11 artificial cases (including a localhost HTTP download); the complete candidate artificial suite passed 29 tests in the existing Python 3.12.3 container. Eight internal export-schema cases passed. All 615 saved structures passed the full schema/value allowlist and retained their original compressed bytes. The initial road archive at this stage was installed locally through the public fetcher, validating all 620 members against its pinned manifest. Station identifiers and offsets are supplied separately.

At this input-preparation stage, road metrics, fixed pilots, full comparison and downstream Gate D had not run. The completed numerical checks are described below; publication is still a separate action.

## Road-measurement extension: fixed pilot

The new restoration/measurement tests first failed before implementation (10 cases), then passed. The complete isolated candidate artificial suite passed 39 tests. A separate verifier test confirms that integer differences, missing-reason differences and values outside the predeclared tolerance fail. Raw RED/GREEN logs are retained with the internal review evidence.

The fixed pilot records r000001, r000007 and r000336 at 600/800/1000 m matched 351 saved cells exactly as parsed numeric values; maximum finite absolute/relative difference was zero. Missing reasons and selected graph invariants also matched. The small-network record retains its exclusion from the adopted fit population. Pilot measurement elapsed time was approximately 172 seconds.

Gate M uses the existing metric-test tolerance (relative/absolute 1e-9), with exact integer/missingness checks. At the pilot stage, unchanged main Gate D and the full 615-record Gate M remained pending. They were subsequently run as described below. No publication approval is implied.

## Full fixed-road verification for paper1-v0.2.0 (2026-11-17)

All 615 fixed road records at 600, 800 and 1,000 m (71,955 cells, including missingness) match exactly as parsed numeric values. Missing reasons and graph invariants also match. The newly measured 800 m indicators pass the unchanged main-analysis Gate D (1e-12 numerical tolerances and exact ordered top-5/10/20 candidates for main and Clip). The 611-station selection population, 614-station fit/main population, fixed eight features and 43 affected Clip station IDs are preserved. The 600/1,000 m input and range-specific fit checks also pass; other sensitivity analyses were not rerun.

Gate M maximum absolute difference: 0; maximum relative difference: 0. The complete check covers 1,845 group/radius cases, 106 missing-reason entries and 1845 invariant records. The measured 800 m main similarity matrix maximum absolute difference is 0.0.

The original three-group pilot was reused with identical input/code/output hashes. The remaining 612 groups were measured once, using isolated processes with startup numerical-library threads fixed to one; controlled supervisor transitions preserved completed outputs and did not repeat group measurements. The unchanged metric module and existing main analysis were checked separately. Original expected values, source indicators, quality ledger and published numerical inputs were not edited.

The final notice-only archive has 621 verified members. Its 615 compressed structures, origins and definition retain exactly the bytes used in measurement; only notices and the archive manifest were revised. The public fetcher validated the final archive locally. These numerical checks used the local archive and did not require external road acquisition. The release configuration now pins the archive asset URL and hashes. Public retrieval is a separate distribution check; it is not a repeat of road measurement. Final independent and Claude reviews and the author's approval of the exact release scope were recorded before publication preparation.

## Public measurement-to-main interface

The public `measurement_to_main` adapter was added after full numerical verification. Its two artificial cases cover the 615-road/station join, 39-column/null preservation, unchanged source/expected/registry/quality bytes, and rejection of duplicate, missing, wrong-radius or existing-output inputs. The final complete candidate suite passed **41 tests** in 2.41 seconds in the same reference environment.

The adapter was then executed on all 615 already-measured 800 m JSON outputs. Its entire six-file main-input directory matched the earlier Gate-D-passing input directory byte for byte, including expectations and manifest. The generated indicator TSV also matches the original saved TSV SHA256. This checks the published interface without repeating road measurement or the identical main calculation. README supplies all-615 explicit-ID measurement and the two subsequent public commands; the private parallel supervisor is not a required or published component.
