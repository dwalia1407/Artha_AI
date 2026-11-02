# Day 1 — Dataset, labels and classification task

Prepared 2 November 2026 by Disha. Day labels identify planned milestones; they do not claim earlier delivery. Status: saved locally, not sent; recipient acceptance pending.

Approved source: Sumeetgpt/indian-transaction-categorization-synthetic, revision `3d999ade82265b95f66db004f967cc3219009df6`. The publisher declares MIT and entirely synthetic data; no standalone LICENSE file was present in the downloaded source. Source: https://huggingface.co/datasets/Sumeetgpt/indian-transaction-categorization-synthetic

The approved research cleanup yields 539 spending-category candidates across 13 labels. Income, transfers and other reviewed money movements are not spending-classifier labels. Do not infer transaction type or financial totals from category predictions.

[Approved input schema and labels](../../../../ml/contracts/v2/README.md): transaction_id, description, category, group_id. The full frozen dataset is in the linked folder; a separate sample copy is unnecessary. Use only training rows for initial development/examples so validation and test examples do not become training material.

Day 2 below supplies the final manifest and shared preparation. This is synthetic-only evaluation, not a claim of real bank-statement accuracy.
