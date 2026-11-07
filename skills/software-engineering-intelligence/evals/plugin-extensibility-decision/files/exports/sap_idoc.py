"""SAP IDoc ORDERS05 export for Mercato SpA (built 2026-03)."""
import xml.etree.ElementTree as ET
from itertools import groupby


def render(rows: list[dict]) -> bytes:
    root = ET.Element("ORDERS05")
    for order_no, lines in groupby(rows, key=lambda r: r["order_no"]):
        idoc = ET.SubElement(root, "IDOC", BEGIN="1")
        header = ET.SubElement(idoc, "E1EDK01", SEGMENT="1")
        ET.SubElement(header, "BELNR").text = str(order_no)
        for line in lines:
            item = ET.SubElement(idoc, "E1EDP01", SEGMENT="1")
            ET.SubElement(item, "MENGE").text = str(line["quantity"])
            ET.SubElement(item, "VPREI").text = str(line["unit_price"])
            material = ET.SubElement(item, "E1EDP19", SEGMENT="1")
            ET.SubElement(material, "QUALF").text = "002"
            ET.SubElement(material, "IDTNR").text = line["sku"]
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
