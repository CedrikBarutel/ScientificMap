# Project Review: Personalized Academic Mailing List

## Current state

The project already has a coherent local pipeline for building an academic contact dataset. It can:

1. collect profiles from configured public/official sources;
2. deduplicate people;
3. enrich records with publication keywords when OpenAlex network access is enabled;
4. build graph edges from shared institution, department, keywords, linked profiles, and coauthorship records;
5. generate topic tables and interactive HTML maps;
6. create seminar candidate lists for a given topic;
7. export a campaign CSV for manual review only.

The offline test suite passes with `python3 -m unittest discover -s tests -v`.

## What is good

- The command-line interface is clear and easy to extend.
- The project keeps collection, enrichment, graph construction, seminar suggestions, and campaign export in separate modules.
- The data model stores provenance through `source_urls`, which is essential for manual verification.
- The campaign export explicitly avoids sending emails and marks every row as `needs_review`.
- The robot-aware fetcher and rate-limit settings are good first steps for responsible collection.

## Gaps and risks

- The previous schema did not store a physical `location`, although the project goal mentions localisation.
- The campaign exporter previously accepted any nonempty email-like field. This could accidentally include malformed or obfuscated contacts.
- The HTML parser is generic and will miss many modern university pages where people cards are rendered in custom markup or JavaScript.
- The matching logic is still keyword-based, so it can miss semantically close topics and over-rank repeated generic keywords.
- There is no strong opt-out database yet; opt-out status is only preserved from the previous campaign CSV.
- The current data includes a broad TU Wien Algorithms and Complexity sample plus the newly curated biophysics/soft-matter records. For a focused seminar campaign, the dataset should be filtered by field before export.

## Changes made in this version

- Added a `location` field to people records and campaign/seminar outputs.
- Updated the HTML maps to display and search by location.
- Added a stricter email validation check before campaign export.
- Added curated Vienna-area biophysics, soft-matter, microscopy, tissue mechanics, and biological-network records from official public pages.
- Added `data/raw/vienna_biophysics_people.csv` as the curated source table.
- Rebuilt processed people, edges, topics, maps, network report, seminar candidates, and a sample reviewed campaign export.

## Recommended next steps

1. Add a source-specific parser for each target institution instead of relying only on generic selectors.
2. Add an explicit `do_not_contact` or `opt_out` table independent of campaign exports.
3. Add an `email_status` field such as `valid`, `missing`, `obfuscated_on_source`, or `needs_manual_verification`.
4. Add a `field_cluster` field, e.g. `biophysics`, `soft matter`, `CS`, `microscopy`, to avoid mixing unrelated Vienna academics.
5. Replace simple substring topic matching with embeddings or a controlled vocabulary.
6. Keep campaign export manual-only; add templates that include why the recipient is relevant and a clear opt-out sentence.
