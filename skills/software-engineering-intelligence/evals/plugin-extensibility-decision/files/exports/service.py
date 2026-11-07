"""Order exports: one file per date range, in the format the tenant picks in the admin."""
import csv
import io
import json
from datetime import date

from . import sap_idoc
from .db import ORDER_COLUMNS, fetch_order_lines

FORMATS = ("csv", "csv_semicolon", "csv_latin1", "xlsx", "json", "sap_idoc")


class ExportService:
    def __init__(self, conn):
        self.conn = conn

    def export(self, tenant_id: int, fmt: str, date_from: date, date_to: date) -> bytes:
        rows = fetch_order_lines(self.conn, tenant_id, date_from, date_to)
        if fmt == "csv":
            return self._csv(rows, delimiter=",", encoding="utf-8")
        elif fmt == "csv_semicolon":
            # Nordgross: semicolons and decimal commas
            for row in rows:
                for key in ("unit_price", "net_amount", "vat_amount", "gross_amount"):
                    row[key] = str(row[key]).replace(".", ",")
            return self._csv(rows, delimiter=";", encoding="utf-8")
        elif fmt == "csv_latin1":
            # Baltic Foods: ISO-8859-1 and dd.mm.yyyy dates
            for row in rows:
                row["order_date"] = row["order_date"].strftime("%d.%m.%Y")
            return self._csv(rows, delimiter=",", encoding="latin-1")
        elif fmt == "xlsx":
            from openpyxl import Workbook

            workbook = Workbook()
            sheet = workbook.active
            sheet.append(ORDER_COLUMNS)
            for row in rows:
                sheet.append([row[c] for c in ORDER_COLUMNS])
            buffer = io.BytesIO()
            workbook.save(buffer)
            return buffer.getvalue()
        elif fmt == "json":
            return json.dumps(rows, default=str).encode()
        elif fmt == "sap_idoc":
            return sap_idoc.render(rows)
        else:
            raise ValueError(f"unknown export format: {fmt}")

    def _csv(self, rows: list[dict], delimiter: str, encoding: str) -> bytes:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=ORDER_COLUMNS, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)
        return buffer.getvalue().encode(encoding)
