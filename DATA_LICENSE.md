# Data licensing scope for the release

The software, tests and author-created technical documents use MIT. That grant does not cover the research data. The following terms apply to the data in this release.

## Numerical database and classification decisions

To the extent the author holds database rights, the selected numerical database under `data/main/`, `data/sensitivity/` and `data/regional_distance/`, including inputs, expected results, fixed scales, pair distances, station candidate lists and summaries, is available under the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/). The same treatment applies to the author-created database rights in `data/supplement/park_classification.tsv` and `data/supplement/park_area_decisions.json`.

© OpenStreetMap contributors. The original OpenStreetMap database is available under ODbL 1.0. This release policy does not claim that numerical aggregation, removal of geometry or storage as an expected result exempts a derived database from the source conditions. See [OpenStreetMap copyright](https://www.openstreetmap.org/copyright).

ODbL governs database rights, not every separate right in each item. Station IDs and other station-derived contents retain the station provider's applicable terms; regional memberships and regional summaries retain the reference-layer attribution. These third-party rights are not purportedly replaced by the author's grant.

## Separately identified third-party inputs

| Input | Applicable source conditions |
| --- | --- |
| `data/supplement/station_representatives.tsv` | Derived from 駅データ.jp; its processing and third-party provision terms remain applicable. Distribution is free of charge. |
| `data/supplement/tmu_land_readjustment_20231208.geojson` | Unchanged TMU archive input under the archive's original terms and required attribution; not relicensed by the author under MIT or ODbL. |

See `SOURCE_NOTICES.md` for the providers, source editions, links and required notices. The data manifests and data-directory notices do not extend the MIT grant to these files.

## Disclosure package

The package provides the complete selected numerical tables, the upstream transformation descriptions in `METHODS.md`, and the additional adopted classifications, station definitions/representatives and regional reference input in `data/supplement/`. It is prepared as the concrete disclosure corresponding to the database and method/additional-content alternatives in ODbL section 4.6. Its scope has to be read with the distinct rights over third-party contents above; it is not a certification of every legal classification.

The original OSM history and contributor personal metadata are excluded. The original history download URL and actual retrieval time remain unverified. The executable code starts from saved indicators; the upstream method description is not an executable road-extraction implementation. No altered scientific result or new road measurement is introduced by this disclosure package.
