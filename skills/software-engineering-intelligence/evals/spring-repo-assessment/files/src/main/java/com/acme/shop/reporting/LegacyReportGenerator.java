package com.acme.shop.reporting;

import java.util.List;
import java.util.Map;

// Generates the yearly CSV that accounting imports into their old tool. Format is fixed by that tool.
public class LegacyReportGenerator {
    public String gen(List<Map<String, Object>> d, int y, boolean f) {
        String r = "";
        int c = 0;
        for (int i = 0; i < d.size(); i++) {
            Map<String, Object> m = d.get(i);
            if (m.get("y") != null && ((Integer) m.get("y")) == y) {
                if (f) {
                    if (m.get("s") != null && m.get("s").equals("PAID")) {
                        r = r + m.get("id") + ";" + m.get("t") + ";" + m.get("c") + "\r\n";
                        c++;
                    }
                } else {
                    if (m.get("s") != null && !m.get("s").equals("CANCELLED")) {
                        r = r + m.get("id") + ";" + m.get("t") + ";" + m.get("c") + "\r\n";
                        c++;
                    }
                }
            }
        }
        r = r + "COUNT;" + c + "\r\n";
        return r;
    }
}
