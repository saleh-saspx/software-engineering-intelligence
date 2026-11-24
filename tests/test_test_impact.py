"""scripts/test_impact.py: change classification and the proposed test plan."""
import json
import unittest

from _support import Tree, run_script

import test_impact

BASE = {
    "app/__init__.py": "",
    "app/pricing/__init__.py": "",
    "app/pricing/discount.py": """
        def discount(amount, rate):
            return amount * rate
    """,
    "app/quote.py": """
        from app.pricing.discount import discount

        def quote(amount):
            return amount - discount(amount, 0.1)
    """,
    "app/repo/__init__.py": "",
    "app/repo/orders.py": """
        def save(conn, order):
            conn.execute("INSERT INTO orders (id, total) VALUES (%s, %s)", (order.id, order.total))
    """,
    "tests/test_discount.py": """
        from app.pricing.discount import discount

        def test_discount():
            assert discount(100, 0.1) == 10
    """,
    "tests/test_quote.py": """
        from app.quote import quote

        def test_quote():
            assert quote(100) == 90
    """,
    "docs/guide.md": "# Guide\n",
    "db/migrations/V1__init.sql": "CREATE TABLE orders (id bigint PRIMARY KEY, total numeric(12,2));\n",
    "docker-compose.yml": "services:\n  db:\n    image: postgres:16\n",
}


def plan_of(tree, **kw):
    return test_impact.scan(tree.path, kw.get("base"), None, kw.get("files"), 3)


class TestImpact(unittest.TestCase):
    def setUp(self):
        self.tree = Tree(BASE)
        self.tree.commit_all("base")

    def tearDown(self):
        self.tree.__exit__()

    def classes(self, res):
        return {(g["group"], g["class"]) for g in res["plan"]}

    def test_docs_only_change_needs_no_tests(self):
        self.tree.write({"docs/guide.md": "# Guide\n\nMore words.\n"})
        res = plan_of(self.tree)
        self.assertEqual([c["type"] for c in res["changes"]], ["docs"])
        self.assertIn(("All test levels", "Not necessary"), self.classes(res))
        self.assertNotIn("Required", {g["class"] for g in res["plan"]})

    def test_source_change_selects_direct_and_transitive_tests(self):
        self.tree.write({"app/pricing/discount.py": "def discount(amount, rate):\n    return round(amount * rate, 2)\n"})
        res = plan_of(self.tree)
        change = res["changes"][0]
        self.assertEqual(change["type"], "source")
        self.assertIn("money", change["flags"])
        self.assertEqual(change["tests"].get("tests/test_discount.py"), 1)
        self.assertGreater(change["tests"].get("tests/test_quote.py", 0), 1)
        groups = {g["class"]: g for g in res["plan"]}
        self.assertTrue(any(g["class"] == "Required" and "importing or named after" in g["group"] for g in res["plan"]))
        self.assertTrue(any(g["class"] == "Recommended" and "through imports" in g["group"] for g in res["plan"]))
        self.assertIn(("Database engine matrix", "Not necessary"), self.classes(res))
        self.assertIn("Recommended", groups)

    def test_engine_specific_sql_requires_that_engine(self):
        self.tree.write({"app/repo/orders.py": """
            def save(conn, order):
                conn.execute("INSERT INTO orders (id, total) VALUES (%s, %s) "
                             "ON CONFLICT (id) DO UPDATE SET total = EXCLUDED.total", (order.id, order.total))
        """})
        res = plan_of(self.tree)
        change = res["changes"][0]
        self.assertEqual(change["type"], "data-access")
        self.assertEqual(change["engines"], ["postgresql"])
        db_groups = [g for g in res["plan"] if g["group"].startswith("Database tests")]
        self.assertEqual(len(db_groups), 1)
        self.assertEqual(db_groups[0]["class"], "Required")
        self.assertIn("(C)", db_groups[0]["engines"])
        self.assertIn("orders.py", " ".join(res["gaps"]))

    def test_portable_query_change_runs_on_production_engine(self):
        self.tree.write({"app/repo/orders.py": """
            def save(conn, order):
                payload = order.raw.decode("utf-8")  # not Oracle DECODE
                conn.execute("UPDATE orders SET total = %s WHERE id = %s", (order.total, order.id))
        """})
        res = plan_of(self.tree)
        change = res["changes"][0]
        self.assertEqual(change["engines"], [], "lower-case .decode( in code is not engine-specific SQL")
        db_groups = [g for g in res["plan"] if g["group"].startswith("Database tests")]
        self.assertIn("PostgreSQL (B)", db_groups[0]["engines"])

    def test_migration_change_plans_apply_and_lint(self):
        self.tree.write({"db/migrations/V2__idx.sql": "CREATE INDEX idx_orders_total ON orders (total);\n"})
        res = plan_of(self.tree)
        self.assertEqual(res["changes"][0]["type"], "migration")
        names = " ".join(g["group"] for g in res["plan"] if g["class"] == "Required")
        self.assertIn("Apply", names)
        self.assertIn("migration_lint.py", names)

    def test_signals_come_from_the_changed_lines(self):
        self.tree.write({"app/quote.py": BASE["app/quote.py"] + "\n\ndef quote_label(amount):\n    return f'{amount}'\n",
                         "app/pricing/discount.py": "def discount(amount, rate):\n    return amount * rate  # same\n"})
        self.tree.commit_all("money everywhere")
        self.tree.write({"app/quote.py": "# syntax and author notes only\n" + BASE["app/quote.py"]})
        res = plan_of(self.tree)
        change = res["changes"][0]
        self.assertEqual(change["flag_scope"], "change")
        self.assertNotIn("money", change["flags"], "money words elsewhere in the file are not part of this change")
        self.assertFalse(any(g["group"].startswith("Boundary tests") for g in res["plan"]))

    def test_tokens_not_substrings(self):
        self.assertEqual(test_impact.signal_flags("app/models/author.py", "syntax = load_balancer.feed()"), set())
        self.assertEqual(test_impact.signal_flags("app/x.py", "unit_price = 3"), {"money"})
        self.assertEqual(test_impact.signal_flags("app/x.py", "checkPasswordHash(user)"), {"security"})

    def test_test_names_derived_from_the_file_name(self):
        self.tree.write({"tests/test_discount_rounding.py": "from app.pricing import discount\n",
                         "app/pricing/discount.py": "def discount(amount, rate):\n    return amount * rate * 1\n"})
        res = plan_of(self.tree)
        change = next(c for c in res["changes"] if c["file"] == "app/pricing/discount.py")
        self.assertEqual(change["tests"].get("tests/test_discount_rounding.py"), 1)

    def test_classification_of_tricky_paths(self):
        c = test_impact.classify
        self.assertEqual(c("app/docs/openapi_builder.py", "def build(): pass")[0], "source")
        self.assertEqual(c("prisma/schema.prisma", "model A { id Int @id }")[0], "data-access")
        self.assertEqual(c("src/main/resources/mapper/OrderMapper.xml", "<mapper namespace='x'>")[0], "data-access")
        self.assertEqual(c("app/stock.py", "Stock.objects.select_for_update().get(pk=1)")[0], "data-access")
        self.assertEqual(c("app/views/orders/show.json.erb", "{}")[0], "contract")
        self.assertEqual(c("app/config.py", "FLAG = True")[0], "config")
        self.assertEqual(c("tests/conftest.py", "import pytest")[0], "test-support")

    def test_shared_constructs_follow_the_application_engine(self):
        with Tree({"requirements.txt": "psycopg2==2.9\n",
                   "app/repo/report.py": "q = \"SELECT TO_CHAR(created_at, 'YYYY') FROM orders\"\n"}) as t:
            res = test_impact.scan(t.path, None, None, ["app/repo/report.py"], 3)
        group = next(g for g in res["plan"] if g["group"].startswith("Database tests"))
        self.assertIn("PostgreSQL", group["engines"])
        self.assertNotIn("Oracle", group["engines"])

    def test_option_like_refs_are_refused(self):
        with self.assertRaises(SystemExit):
            test_impact.scan(self.tree.path, "--output=/tmp/should-not-exist", None, None, 3)

    def test_files_mode_without_git(self):
        with Tree({"src/util.py": "def f():\n    return 1\n"}) as t:
            res = test_impact.scan(t.path, None, None, ["src/util.py"], 3)
        self.assertEqual(res["changes"][0]["type"], "source")
        self.assertTrue(any("New or missing tests" in g["group"] for g in res["plan"]))

    def test_cli_outputs(self):
        self.tree.write({"app/pricing/discount.py": "def discount(a, r):\n    return a * r\n"})
        md = run_script("test_impact.py", str(self.tree.path))
        self.assertEqual(md.returncode, 0, md.stderr)
        self.assertIn("Required", md.stdout)
        js = run_script("test_impact.py", str(self.tree.path), "--json")
        self.assertEqual(js.returncode, 0, js.stderr)
        self.assertIn("plan", json.loads(js.stdout))


if __name__ == "__main__":
    unittest.main()
