"""
City reference data processing.

Primary layer: LivingCost (221 cities) -> base city reference.
Enrichment layer: 30-city socioeconomic dataset -> adds gdp / population /
eol_score for cities that also exist in the 221-city master. We do NOT
pull in the 30-city dataset's own cost/rent/salary columns because those
duplicate the LivingCost columns already in the master (see Non-Negotiable
Rule: don't merge without a defined purpose / don't create redundant
features).

City matching:
The 30-city dataset has two names that do not exact-match the 221-city
key: "hyderabad" and "kochi". Inspection of the 221-city names shows the
master carries these as "Hyderabad, Telangana" and "Kochi, Kerala" (i.e.
the same cities, state-qualified). This is an inspected, objectively
supported mapping, not a guess, and is applied explicitly below.

Output: data/processed/city_master.csv
"""

import pandas as pd
from utils import RAW_DIR, PROCESSED_DIR, REPORTS_DIR, make_city_key, write_log, check_duplicates

LC_SRC = RAW_DIR / "livingcost_india_all_inr (4).csv"
ENRICH_SRC = RAW_DIR / "merged_cities_data (2).csv"
OUT = PROCESSED_DIR / "city_master.csv"
LOG = REPORTS_DIR / "city_processing_log.md"

# Explicit, inspected mapping for names that don't exact-match on the
# normalized key. Left side = 30-city key, right side = 221-city key.
EXPLICIT_CITY_KEY_MAP = {
    "hyderabad": "hyderabad, telangana",
    "kochi": "kochi, kerala",
}


def process():
    lc = pd.read_csv(LC_SRC)
    lc.columns = [c.strip() for c in lc.columns]
    lc_missing = int(lc.isna().sum().sum())
    lc_dup = check_duplicates(lc)

    lc["city_key"] = make_city_key(lc["City"])
    lc_dup_keys = int(lc["city_key"].duplicated().sum())

    enrich = pd.read_csv(ENRICH_SRC)
    enrich.columns = [c.strip() for c in enrich.columns]
    enrich_missing = enrich.isna().sum()
    enrich_dup = check_duplicates(enrich)

    enrich["city_key"] = make_city_key(enrich["city"])
    unmatched_before = sorted(set(enrich["city_key"]) - set(lc["city_key"]))
    enrich["city_key"] = enrich["city_key"].replace(EXPLICIT_CITY_KEY_MAP)

    enrich_new = enrich[["city_key", "gdp_nominal_inr_billion", "ua_population_lakhs", "eol_score"]].copy()
    enrich_dup_keys = int(enrich_new["city_key"].duplicated().sum())

    merge_report = {
        "lc_rows": len(lc), "enrich_rows": len(enrich_new),
        "lc_dup_keys": lc_dup_keys, "enrich_dup_keys": enrich_dup_keys,
    }

    city_master = lc.merge(enrich_new, on="city_key", how="left", validate="one_to_one")

    unmatched_after = sorted(set(enrich["city_key"]) - set(city_master["city_key"]))
    matched_count = enrich_new["city_key"].isin(city_master["city_key"]).sum()

    city_master.to_csv(OUT, index=False)

    lines = [
        "# City Data Processing Log",
        "",
        "## LivingCost (base, 221-city reference)",
        f"- Shape: {lc.shape}",
        f"- Missing values (total cells): {lc_missing}",
        f"- Duplicate rows: {lc_dup}",
        f"- Duplicate city_key values: {lc_dup_keys}",
        "",
        "## 30-city socioeconomic enrichment",
        f"- Shape: {enrich.shape}",
        f"- Duplicate rows: {enrich_dup}",
        f"- eol_score missing: {int(enrich_missing.get('eol_score', 0))}",
        f"- matched_source_url_in_master missing: {int(enrich_missing.get('matched_source_url_in_master', 0))}",
        f"- Fields pulled into the master (new info only, not already in LivingCost):"
        f" gdp_nominal_inr_billion, ua_population_lakhs, eol_score",
        f"- composite_score, gdp_norm, pop_norm, eol_norm_filled deliberately EXCLUDED:"
        f" composite_score is derived from the three normalized inputs, so keeping all of them"
        f" together would be redundant / leak the same signal multiple times into any downstream model.",
        "",
        "## City key matching",
        f"- Unmatched 30-city keys before explicit mapping: {unmatched_before}",
        f"- Explicit mapping applied (inspected, not guessed): {EXPLICIT_CITY_KEY_MAP}",
        f"- Unmatched 30-city keys after explicit mapping: {unmatched_after}",
        f"- 30-city rows successfully matched into master: {matched_count} / {len(enrich_new)}",
        "",
        "## Merge validation (validate='one_to_one')",
        f"- {merge_report}",
        f"- Row count before merge: {lc.shape[0]}, after merge: {city_master.shape[0]}"
        f" (must match for a left join with unique keys on both sides)",
        "",
        f"Output: `data/processed/city_master.csv`, shape {city_master.shape}",
    ]
    write_log(LOG, lines)
    print(f"[CITY] master shape={city_master.shape}, matched enrichment rows={matched_count}/{len(enrich_new)}")
    return city_master


if __name__ == "__main__":
    process()
