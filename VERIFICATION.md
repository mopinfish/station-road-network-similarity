# Verification of the local candidate

Verification date: 2026-11-16. This records numerical reproduction, not publication approval or validation of every scientific interpretation. Reference environment details are in `environment.json`; other CPUs/BLAS builds are not verified.

| Scope | Result |
| --- | --- |
| Complete candidate test suite | 18 tests passed, no skips/deselections |
| Main analysis | Selection populations 611/614; selected features/order, scales, vectors, dominance, Clip comparisons and fixed six pairs match. Main 614 × 614 similarity matrix maximum difference 0.0. Ordered top-5/10/20 candidates match exactly. |
| Sensitivity | 395,775 checks passed, including 31,912 saved ordered candidate lists and 119 display cells in adopted tables 6–8 |
| Regional/distance | Regional and indicator distributions, Spearman and 4,000 bootstrap rows match exactly; 800 fold fits, 160 repeat rows and 8 model summaries match exactly in the adopted eight-thread fitting environment; table 9/10 display values match |
| Cross-module boundary | Recomputed main matrix equals the regional/distance input matrix, all 614 × 614 elements |

Each module was exercised from an independent temporary tree containing only its code and declared data. No private analysis module or manuscript was required at runtime. Inputs/expected outputs were kept separate, and original source files were preserved.

An initial one-thread regional/distance run matched regional, correlation and all bootstrap values but failed the fixed tolerances for some linear-fit fields. A targeted startup-eight-thread CV reconciliation reproduced every CV field exactly. Finally, the documented full regional/distance CLI was executed from the separate local candidate directory with eight startup threads and an empty PYTHONPATH: it completed in about 330 seconds with exit code 0 and all reference checks passing. This final run covers both complete bootstrap conditions and all CV fits in a single invocation. Earlier failed runs remain in the private maintenance record; expected values and tolerances were not changed.

Independent Codex checks include separate reconstruction of main selection and candidates, and 2,452 station-comparison rows for Clip and the 600–800 m range comparison. Independent Codex accepted all three implementations with no unresolved major findings; Claude approved the final code/document review after the environment explanation was clarified. Their detailed records remain in the private maintenance report. The public candidate excludes internal review conversations and private source paths.

Upstream road extraction/measurement, alternative environments, public download/retrieval and publication are outside this verification. The private research repository's entire test suite was not rerun because its production code/configuration was unchanged. Future updates must test the affected scientific rules and paper settings as described in `UPDATING.md`.

The later disclosure supplement was checked independently against saved sources: 1,545 classification rows, 615 station-group rows, five area decisions and two retained references, and the unchanged 69-feature regional layer. Existing numerical inputs and source/test code retain their previously verified hashes. The supplement adds provenance and input disclosure only; numerical analysis was not rerun for these document/data-transcription changes.
