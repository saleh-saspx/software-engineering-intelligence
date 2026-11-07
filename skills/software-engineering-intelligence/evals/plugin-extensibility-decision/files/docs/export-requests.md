# Export format requests (last 12 months)

| # | Date | Tenant | Asked for | Differs from our standard CSV by | Status |
|---|---|---|---|---|---|
| 1 | 2025-11 | Nordgross | CSV with semicolons and decimal commas | delimiter, decimal separator | built (`csv_semicolon`) |
| 2 | 2025-12 | Baltic Foods | CSV in ISO-8859-1 with dd.mm.yyyy dates | encoding, date format | built (`csv_latin1`) |
| 3 | 2026-01 | Kessler AG | Fixed-width file for their bank's import | fixed-width column layout | open |
| 4 | 2026-02 | Alvarez Distribución | CSV with 6 of our 14 columns and Spanish headers | column selection, header names | open |
| 5 | 2026-03 | Mercato SpA | SAP IDoc XML (ORDERS05) | different structure (XML) | built (`sap_idoc`) |
| 6 | 2026-04 | Nordgross | Amounts in cents, without decimals | number format | open |
| 7 | 2026-06 | Baltic Foods | Excel with a totals row | extra totals row | open |
| 8 | 2026-08 | Kessler AG | A second fixed-width layout for another bank | fixed-width column layout | open |
| 9 | 2026-10 | Hofmann Großhandel | JSON Lines for their data warehouse | different serialisation (JSON Lines) | open |
