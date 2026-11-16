# Data availability and provenance

Selected derived tables and fixed numerical inputs are distributed in [paper1-v0.1.1](https://github.com/mopinfish/station-road-network-similarity/releases/tag/paper1-v0.1.1). The original software and accompanying technical documentation use MIT (see `LICENSING.md`); the data terms and independently identified source conditions are set out in `DATA_LICENSE.md` and `SOURCE_NOTICES.md`.

## Sources behind the saved indicators

| Source | Recorded version and provenance | Release boundary |
| --- | --- | --- |
| OpenStreetMap history, Kanto | Snapshot reconstructed at 2026-07-27T15:04:33Z with osmium-tool 1.16.0; original history SHA256 `936240e22ed184ae165d24a6b86830830f8e9a7925f5b7f1bccffb3497315d98`; snapshot SHA256 `0e9906f1d9d57832ee5052e7481ca293552276e32c352bd95857436733b1ab8d` | Raw history and snapshot excluded. Actual original download URL and download time are unconfirmed; the snapshot time is not a download time. |
| 駅データ.jp | Free station data, version 2026-07-31, fetched 2026-10-14T00:34:43.316110Z; original CSV SHA256 `0e679ce1a254d78134b0e903ddb0a7449cf688ae7c2637baea8940b34e2af030` | Saved station group identifiers are used for joining; adopted group definitions and representative coordinates are provided in the supplement. Original full station CSV excluded. Tokyo active rows yielded 615 groups from 943 records before analysis-specific exclusions. |
| 東京都立大学 災害復興GISデータアーカイブ | `GKE_LandReadjustment_Tokyo_20231208.geojson`, fetched 2026-10-16T14:44:39Z; SHA256 `40e73522b3d57cebac9d3b10b22b751207c342e716ea5b6f24d615c527f64d5d` | Saved region membership is used; the unchanged adopted GeoJSON is included as a separately identified supplemental input under its original terms. The archive traces the 1931 帝都復興事業誌 map; it does not certify legal boundary precision. |

Park and garden areas were derived from the saved OSM snapshot, not an additional external park register. The release keeps the adopted station sets and conditions. It does not promise that these original input bytes can still be downloaded from current source pages.

## Attribution and distribution decisions

OpenStreetMap data: © OpenStreetMap contributors. Consult the [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) and [Geofabrik technical information](https://download.geofabrik.de/technical.html). The database rights and third-party contents are covered separately in `DATA_LICENSE.md`; no blanket exemption for aggregated values is asserted. Original authenticated history metadata are not bundled.

Station data source: [駅データ.jp](https://www.ekidata.jp/dl/?p=1), [terms](https://www.ekidata.jp/agreement.php). The recorded download URL was `https://www.ekidata.jp/dl/f.php?t=5&d=20260731`. The terms reviewed on 2026-11-16 permit processed and unprocessed third-party provision subject to their conditions; unprocessed provision must be free.

Regional data source: 東京都立大学 災害復興GISデータアーカイブ, [Tokyo land readjustment GeoJSON](https://masumura.ues.tmu.ac.jp/dr_gis/download/gke_landreadjustment_tokyo_json/), [terms](https://masumura.ues.tmu.ac.jp/dr_gis/termsofconditions/). Preserve the required source attribution and any applicable individual dataset instructions; do not apply the code's MIT license to third-party data automatically.

The selected files, rights notices, destination and version were approved for this release. The release includes only the selected files listed in `manifest.json`.

## Verification and provenance records

The release manifest identifies selected package files by size and SHA256. Private maintenance records additionally bind these files to original saved outputs and transformation steps; private filesystem paths and original operational manifests are intentionally not bundled. Expected results are references for checking calculations, not substitute calculation inputs.

## Concrete disclosure package

The supplement preserves 1,545 adopted structural park classifications, five adopted area decisions and two retained-area references, 615 original station groups with saved representative coordinates, and the exact 69-feature TMU input. Counts describe saved material, not new analysis. `METHODS.md` covers the upstream transformations and the 39-to-29-to-8 indicator procedure; it is not a road-generation executable. The selected numerical database, methods and additional contents are provided together as the ODbL disclosure package. Copyright and conditions over third-party contents remain separate.
