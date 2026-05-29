# RxNav NDC Code Retrieval Tool

Author: Xingran Weng

Version Date: January 25th, 2026

## Overview

This tool automates the retrieval of **NDC (National Drug Code)** and **RxNorm** codes (both branded or generic) for a given drug name by querying the **[RxNav REST API](https://lhncbc.nlm.nih.gov/RxNav/)** — a publicly available drug information service maintained by the U.S. National Library of Medicine (NLM).

The output is a structured CSV file containing NDC codes, RxNorm identifiers, brand names, generic names, and drug type classifications. This is intended to support feasibility and real-world data (RWD) studies that require drug code lists for database querying (e.g., MarketScan, Optum, etc.). 

---

## Folder Structure

```
RxNav/
├── automated_script.py          # Entry point — run this to launch the tool
├── README.md                    # This file
├── drug_codes/                  # Output folder — generated CSV files are saved here
└── root/
    ├── __int__.py               # Package init file
    ├── main.py                  # Interactive menu and orchestration logic
    ├── get_drug_data.py         # Exact search function
    └── get_drug_data_fuzzy_search.py  # Fuzzy (approximate) search function
```

---

## How to Run

### Prerequisites

Ensure the following Python packages are installed:

```bash
pip install requests pandas
```

### Running the Tool

From the `RxNav/` directory, run:

```bash
python automated_script.py
```

You will be prompted with an interactive menu:

```
========================================
  RxNav Drug Data Retrieval Tool
========================================
Select a search mode:
  [1] Exact Search       (get_drug_data)
  [2] Fuzzy Search       (get_drug_data_fuzzy_search)
------------------------------
Enter your choice (1 or 2):
```

After selecting a mode, you will be prompted to enter a drug name:

```
Enter the drug name: dupixent
```

The tool will run and save the results to `drug_codes/<drug_name>_NDC_Code_list.csv`.

---

## Search Modes Explained

### Mode 1 — Exact Search (`get_drug_data.py`)

**Best used when:** You know the precise drug name (brand or generic) as it appears in RxNorm (e.g., `"dupilumab"`, `"Dupixent"`).

**API used:** `GET /REST/drugs.json?name={drug_name}`

**Logic:**

1. Queries the RxNav `/drugs` endpoint with the provided drug name.
2. Parses the `conceptGroup` response to extract all matching RxNorm IDs (`rxcui`) and their associated drug names.
3. Filters out any entries with a null RxCUI (`"0"`).
4. For each RxCUI found:
   - Calls `/REST/rxcui/{rxcui}/allhistoricalndcs.json` to retrieve all historical NDC codes.
   - Calls `/REST/rxcui/{rxcui}/generic.json` to retrieve the associated generic drug (SCD) information.
5. Merges NDC and generic data together (left join on RxCUI).
6. Concatenates all records and saves to CSV.

**When it returns no results:** If the drug name does not match any concept in RxNorm exactly, the tool reports "Not valid drug name or unexpected API response structure."

---

### Mode 2 — Fuzzy Search (`get_drug_data_fuzzy_search.py`)

**Best used when:** You are unsure of the exact spelling, or want to cast a wider net to capture all approximate matches (e.g., `"dupixent"`, `"dupilumab 200mg"`).

**API used:** `GET /REST/approximateTerm.json?term={drug_name}&maxEntries=100`

**Logic:**

1. Queries the RxNav `/approximateTerm` endpoint, returning up to 100 approximate match candidates.
2. Filters candidates to only those sourced from `RXNORM` (excludes other vocabularies).
3. Sorts candidates by match score in descending order.
4. De-duplicates candidates by `rxcui` to avoid redundant lookups.
5. For each unique RxCUI candidate:
   - Calls `/REST/rxcui/{rxcui}/allhistoricalndcs.json` to retrieve all historical NDC codes.
   - Calls `/REST/rxcui/{rxcui}/generic.json` to retrieve the associated generic drug (SCD) information.
6. Merges NDC and generic data together (left join on RxCUI).
7. Concatenates all records and saves to CSV.

**When it returns no results:** If no RxNorm candidates are found in the approximate match response, the tool reports "No RxNorm candidates found for the given drug name."

---

## Output CSV Schema

The output file is saved to `drug_codes/<drug_name>_NDC_Code_list.csv` with the following columns:

| Column         | Description                                                                                |
| -------------- | ------------------------------------------------------------------------------------------ |
| `ndc`          | National Drug Code (NDC) — numeric string                                                  |
| `startDate`    | Date the NDC became active (from RxNav historical data)                                    |
| `endDate`      | Date the NDC was discontinued (if applicable)                                              |
| `rxnorm`       | RxNorm ID (RxCUI) of the matched drug concept                                              |
| `drug_name`    | Brand or concept name associated with the RxNorm ID                                        |
| `rxnorm_scd`   | RxNorm ID of the associated generic (SCD) concept                                          |
| `generic_name` | Generic drug name                                                                          |
| `rxnorm_type`  | RxNorm term type (e.g., `SBD` = branded drug, `SCD` = generic drug, `GPCK` = generic pack) |

---

## API Reference

All data is sourced from the **NLM RxNav REST API** — no API key or authentication is required.

| Endpoint                                     | Purpose                                                          |
| -------------------------------------------- | ---------------------------------------------------------------- |
| `/REST/drugs.json`                           | Exact drug name lookup → returns matching RxNorm concepts        |
| `/REST/approximateTerm.json`                 | Fuzzy/approximate drug name search                               |
| `/REST/rxcui/{rxcui}/allhistoricalndcs.json` | Returns all historical NDC codes for a given RxCUI               |
| `/REST/rxcui/{rxcui}/generic.json`           | Returns the generic (SCD) drug associated with a branded concept |

Full API documentation: [https://lhncbc.nlm.nih.gov/RxNav/APIs/](https://lhncbc.nlm.nih.gov/RxNav/APIs/)

---

## Choosing the Right Search Mode

| Scenario                                            | Recommended Mode      |
| --------------------------------------------------- | --------------------- |
| You have the exact INN (generic name) or brand name | Mode 1 — Exact Search |
| You are unsure of spelling or want broader coverage | Mode 2 — Fuzzy Search |
| The drug has many brand/dose variants               | Mode 2 — Fuzzy Search |
| You want only a targeted list without noise         | Mode 1 — Exact Search |

> **Tip:** Running both modes and comparing the outputs can help validate completeness of the drug code list. For fuzzy match, in the fuzzy match function, you have the flexibility to determine the records returned based on the string match from `maxEntries` parameter.

---

## Known Limitations

- **Internet connection required** — the tool queries the RxNav API in real time.
- **RxNav only covers US drug codes** — NDC codes are US-specific; this tool is not suitable for ex-US drug lookups.
- **Fuzzy search may return false positives** — review the output CSV and filter by `drug_name` or `generic_name` if the result set is too broad.
- **Historical NDCs only** — the tool uses the `allhistoricalndcs` endpoint, which includes both active and discontinued NDCs. Post-processing may be needed to filter to currently marketed products.

---

## Contact

For questions or issues with this tool, please reach out to Xingran Weng (xingran.weng@sanofi.com).
