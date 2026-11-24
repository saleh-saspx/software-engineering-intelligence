"""scripts/test_report.py: honest accounting of what ran, what did not, and the verdict."""
import json
import unittest

from _support import Tree, run_script

import test_report

JUNIT_RUN1 = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="pricing" tests="4">
    <testcase classname="tests.pricing.test_discount" name="test_rounding" time="0.010"/>
    <testcase classname="tests.pricing.test_discount" name="test_max_total" time="0.020"/>
    <testcase classname="tests.orders.test_repo" name="test_upsert" time="1.500">
      <skipped message="PostgreSQL not available"/>
    </testcase>
    <testcase classname="tests.api.test_checkout" name="test_flow" time="0.300">
      <failure message="timeout waiting for stub">Traceback ...</failure>
    </testcase>
  </testsuite>
</testsuites>
"""
JUNIT_RUN2 = """<testsuite name="pricing">
  <testcase classname="tests.pricing.test_discount" name="test_rounding" time="0.011"/>
  <testcase classname="tests.pricing.test_discount" name="test_max_total" time="0.019"/>
  <testcase classname="tests.api.test_checkout" name="test_flow" time="0.280"/>
</testsuite>
"""
PLAN = {"groups": [
    {"name": "pricing unit tests", "class": "Required", "match": ["tests.pricing"], "engines": "none (A)"},
    {"name": "orders on PostgreSQL", "class": "Required", "match": ["tests.orders"], "engines": "PostgreSQL 16 (C)"},
    {"name": "checkout API", "class": "Recommended", "match": ["test_checkout"]},
]}


class ParseAndAnalyse(unittest.TestCase):
    def test_skipped_is_never_counted_as_passed(self):
        results = test_report.parse_junit(JUNIT_RUN1, "run1")
        res = test_report.analyse(results, ["run1"], None, 5)
        run = res["runs"]["run1"]
        self.assertEqual((run["passed"], run["failed"], run["skipped"], run["executed"]), (2, 1, 1, 3))
        self.assertEqual(res["skipped"][0]["message"], "PostgreSQL not available")

    def test_flaky_across_reruns_and_not_run_required_group(self):
        results = test_report.parse_junit(JUNIT_RUN1, "run1") + test_report.parse_junit(JUNIT_RUN2, "run2")
        res = test_report.analyse(results, ["run1", "run2"], PLAN, 5, same_environment=True)
        self.assertEqual([f["id"] for f in res["flaky"]], ["tests.api.test_checkout::test_flow"])
        self.assertEqual(res["failures"], [], "a test that passed on another run is flaky, not a hard failure")
        states = {g["name"]: g["state"] for g in res["groups"]}
        self.assertEqual(states["orders on PostgreSQL"], "not run")
        self.assertEqual(states["pricing unit tests"], "passed")
        self.assertEqual(states["checkout API"], "flaky")
        self.assertEqual(res["verdict"], "not verified")
        self.assertIn("orders on PostgreSQL", res["reasons"][0])

    def test_different_environments_turn_a_pass_and_a_fail_into_a_failure(self):
        pg15 = '<testsuite name="s"><testcase classname="db.Orders" name="test_upsert" time="0.1"/></testsuite>'
        pg16 = ('<testsuite name="s"><testcase classname="db.Orders" name="test_upsert" time="0.1">'
                '<failure message="syntax error at or near MERGE"/></testcase></testsuite>')
        results = test_report.parse_junit(pg15, "pg15") + test_report.parse_junit(pg16, "pg16")
        res = test_report.analyse(results, ["pg15", "pg16"], None, 5)
        self.assertEqual(res["flaky"], [])
        self.assertEqual([(f["id"], f["run"]) for f in res["failures"]], [("db.Orders::test_upsert", "pg16")])
        self.assertEqual(res["environment_dependent"][0]["failed_in"], ["pg16"])
        self.assertEqual(res["verdict"], "failed")

    def test_skips_inside_a_required_group_mean_not_verified(self):
        cases = "".join(f'<testcase classname="tests.db.test_repo" name="t{i}" time="0.01"><skipped message="no docker"/></testcase>'
                        for i in range(49))
        xml = f'<testsuite name="db">{cases}<testcase classname="tests.db.test_repo" name="t49" time="0.01"/></testsuite>'
        plan = {"groups": [{"name": "repository tests on PostgreSQL 16", "class": "Required", "match": ["tests/db/"]}]}
        res = test_report.analyse(test_report.parse_junit(xml, "r"), ["r"], plan, 5)
        self.assertEqual(res["groups"][0]["state"], "incomplete (49 of 50 skipped)")
        self.assertEqual(res["verdict"], "not verified")
        plan["groups"][0]["expected_skips"] = ["tests.db.test_repo"]
        res = test_report.analyse(test_report.parse_junit(xml, "r"), ["r"], plan, 5)
        self.assertEqual(res["verdict"], "verified for the stated scope", "planned skips are reported, not held against")

    def test_path_style_patterns_match_dotted_names(self):
        test = {"id": "tests.pricing.test_discount::test_x", "file": "", "classname": "tests.pricing.test_discount",
                "name": "test_x"}
        self.assertTrue(test_report.matches(test, ["tests/pricing/"]))
        self.assertTrue(test_report.matches(test, ["tests/pricing/test_discount.py"]))
        self.assertFalse(test_report.matches(test, ["tests/orders/"]))

    def test_any_hard_failure_means_failed(self):
        results = test_report.parse_junit(JUNIT_RUN1, "run1")
        plan = {"groups": [{"name": "pricing", "class": "Required", "match": ["tests.pricing"]},
                           {"name": "checkout", "class": "Recommended", "match": ["test_checkout"]}]}
        res = test_report.analyse(results, ["run1"], plan, 5)
        self.assertEqual(res["verdict"], "failed")

    def test_verified_only_when_every_required_group_passed(self):
        results = test_report.parse_junit(JUNIT_RUN2, "run2")
        plan = {"groups": [{"name": "pricing", "class": "Required", "match": ["tests.pricing"]}]}
        self.assertEqual(test_report.analyse(results, ["run2"], plan, 5)["verdict"], "verified for the stated scope")
        plan["groups"].append({"name": "contract", "class": "Recommended", "match": ["tests.contract"]})
        self.assertEqual(test_report.analyse(results, ["run2"], plan, 5)["verdict"], "partially verified")

    def test_plan_without_required_group_is_not_verified(self):
        results = test_report.parse_junit(JUNIT_RUN2, "run2")
        plan = {"groups": [{"name": "pricing", "class": "Recommended", "match": ["tests.pricing"]}]}
        self.assertEqual(test_report.analyse(results, ["run2"], plan, 5)["verdict"], "not verified")

    def test_duplicate_execution_within_one_run(self):
        dup = """<testsuite name="s">
          <testcase classname="a.B" name="t" time="0.1"/>
          <testcase classname="a.B" name="t" time="0.1"/>
        </testsuite>"""
        res = test_report.analyse(test_report.parse_junit(dup, "r"), ["r"], None, 5)
        self.assertEqual(res["duplicates"], [{"id": "a.B::t", "run": "r", "times": 2}])

    def test_go_json_with_rerun_and_package_failure(self):
        lines = [
            {"Action": "run", "Package": "x/pay", "Test": "TestRefund"},
            {"Action": "fail", "Package": "x/pay", "Test": "TestRefund", "Elapsed": 0.2},
            {"Action": "run", "Package": "x/pay", "Test": "TestRefund"},
            {"Action": "pass", "Package": "x/pay", "Test": "TestRefund", "Elapsed": 0.1},
            {"Action": "fail", "Package": "x/broken", "Elapsed": 0.0},
        ]
        text = "\n".join(json.dumps(x) for x in lines)
        res = test_report.analyse(test_report.parse_go_json(text, "go"), ["go"], None, 5)
        self.assertIn("x/pay::TestRefund", [f["id"] for f in res["flaky"]])
        self.assertTrue(any(f["id"].startswith("x/broken") for f in res["failures"]))
        self.assertEqual(res["verdict"], "failed")


class Cli(unittest.TestCase):
    def test_cli_plan_fail_on_and_unsafe_xml(self):
        with Tree({"r1.xml": JUNIT_RUN1, "r2.xml": JUNIT_RUN2, "plan.json": json.dumps(PLAN),
                   "evil.xml": '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e "boom">]><testsuite name="&e;"/>'}) as t:
            ok = run_script("test_report.py", f"1041={t.path / 'r1.xml'}", f"1042={t.path / 'r2.xml'}",
                            "--plan", str(t.path / "plan.json"), "--same-environment")
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIn("not verified", ok.stdout)
            self.assertIn("| 1041 |", ok.stdout)
            gate = run_script("test_report.py", str(t.path / "r1.xml"), str(t.path / "r2.xml"),
                              "--plan", str(t.path / "plan.json"), "--fail-on", "not-run", "--same-environment")
            self.assertEqual(gate.returncode, 1)
            separate = run_script("test_report.py", str(t.path / "r1.xml"), str(t.path / "r2.xml"), "--fail-on", "failed")
            self.assertEqual(separate.returncode, 1, "without --same-environment a failure in one run is a failure")
            evil = run_script("test_report.py", str(t.path / "evil.xml"))
            self.assertEqual(evil.returncode, 2)
            self.assertNotIn("boom", evil.stdout)


class Robustness(unittest.TestCase):
    def test_bom_empty_runs_and_same_basename(self):
        with Tree({"pg15/junit.xml": "\ufeff" + JUNIT_RUN2, "pg16/junit.xml": JUNIT_RUN2,
                   "empty.xml": "<testsuites/>"}) as t:
            two = run_script("test_report.py", str(t.path / "pg15/junit.xml"), str(t.path / "pg16/junit.xml"), "--json")
            self.assertEqual(two.returncode, 0, two.stderr)
            data = json.loads(two.stdout)
            self.assertEqual(len(data["runs"]), 2, "runs are named by path, not by file name")
            self.assertEqual(data["duplicates"], [])
            empty = run_script("test_report.py", str(t.path / "empty.xml"), "--fail-on", "not-run")
            self.assertEqual(empty.returncode, 1)
            self.assertIn("no test executed", empty.stdout)


if __name__ == "__main__":
    unittest.main()
