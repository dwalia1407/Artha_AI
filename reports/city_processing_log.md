# City Data Processing Log

## LivingCost (base, 221-city reference)
- Shape: (221, 13)
- Missing values (total cells): 0
- Duplicate rows: 0
- Duplicate city_key values: 0

## 30-city socioeconomic enrichment
- Shape: (30, 24)
- Duplicate rows: 0
- eol_score missing: 21
- matched_source_url_in_master missing: 4
- Fields pulled into the master (new info only, not already in LivingCost): gdp_nominal_inr_billion, ua_population_lakhs, eol_score
- composite_score, gdp_norm, pop_norm, eol_norm_filled deliberately EXCLUDED: composite_score is derived from the three normalized inputs, so keeping all of them together would be redundant / leak the same signal multiple times into any downstream model.

## City key matching
- Unmatched 30-city keys before explicit mapping: ['hyderabad', 'kochi']
- Explicit mapping applied (inspected, not guessed): {'hyderabad': 'hyderabad, telangana', 'kochi': 'kochi, kerala'}
- Unmatched 30-city keys after explicit mapping: []
- 30-city rows successfully matched into master: 30 / 30

## Merge validation (validate='one_to_one')
- {'lc_rows': 221, 'enrich_rows': 30, 'lc_dup_keys': 0, 'enrich_dup_keys': 0}
- Row count before merge: 221, after merge: 221 (must match for a left join with unique keys on both sides)

Output: `data/processed/city_master.csv`, shape (221, 16)
