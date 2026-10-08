# Traceable demonstration orders

This folder contains 70 unique, source-linked garment reference photos and synthetic
order records used by the Streamlit research demonstration.

The source images and expert garment annotations come from **Clothing Dataset
for Second-Hand Fashion**, version 1, by Farrukh Nauman with RISE Research
Institutes of Sweden AB and Wargön Innovation AB, DOI
`10.5281/zenodo.8386668`. The source dataset is licensed under CC BY 4.0.

The order IDs, prices, retailer assignments, purchase dates, delivery dates and
delivery states in this folder are synthetic research data. They are not real
customer transactions. The reference annotations are displayed for
traceability and are never passed to the image models as predictions.

Generated files:

- `orders.db`: SQLite order repository used by the local and deployed UI.
- `orders.json`: human-readable equivalent of the SQLite records.
- `date_results.json`: deterministic date-validation demonstration results.
- `images/`: 70 SHA-256-deduplicated reference photos copied from the CC BY 4.0 source dataset.
