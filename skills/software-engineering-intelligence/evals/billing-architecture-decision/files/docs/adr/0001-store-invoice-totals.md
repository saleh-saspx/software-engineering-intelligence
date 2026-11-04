# ADR-0001: Store computed invoice totals on the invoice row

## Status
Accepted

## Date
2025-03-02

## Context
The finance dashboard's monthly report lists totals for all customers. Recomputing totals from
invoice lines for every report was slow on the old reporting box. Invoices are immutable once
issued; corrections are made with credit notes, never by editing an invoice.

## Decision
We store subtotal, tax and total on the `invoices` row at issue time and the report reads them
directly.

## Consequences
Positive: the report is a single indexed query.
Negative: totals are duplicated from the lines. If invoices ever become editable, totals can drift;
we must revisit this decision before introducing invoice editing.
