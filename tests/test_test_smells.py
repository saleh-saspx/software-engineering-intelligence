"""scripts/test_smells.py: the duplicate-test-body check (TEST-COST-01) and the checks it must not disturb."""
import unittest

from _support import Tree

import test_smells

PY_BODY = """
    cart = [("apple", 2, 3), ("pear", 1, 5)]
    result = total(cart)
    assert result == 11
"""


def scan(files):
    with Tree(files) as t:
        res = test_smells.scan(t.path, None, 20)
    return {r["check"]: r for r in res["results"]}


class DuplicateBodies(unittest.TestCase):
    def test_python_duplicates_across_files(self):
        got = scan({
            "tests/test_a.py": f"def test_one():{PY_BODY}\ndef test_two():\n    '''copied'''{PY_BODY}",
            "tests/test_b.py": f"def test_three():{PY_BODY}",
        })
        hits = got["duplicate-test-body"]["hits"]
        self.assertEqual(got["duplicate-test-body"]["count"], 1, "one group of three identical tests")
        self.assertIn("test_two", hits[0]["snippet"])
        self.assertIn("tests/test_b.py", hits[0]["snippet"])

    def test_different_parametrisation_is_not_a_duplicate(self):
        got = scan({"tests/test_a.py": (
            f"import pytest\n\n@pytest.mark.parametrize('x', [1])\ndef test_one(x):{PY_BODY}\n"
            f"@pytest.mark.parametrize('x', [2])\ndef test_two(x):{PY_BODY}")})
        self.assertNotIn("duplicate-test-body", got)

    def test_java_duplicates_ignore_comments_and_whitespace(self):
        body = "Order o = new Order();\n        o.add(new Line(\"a\", 2, 3));\n        assertEquals(6, o.total());"
        java = ("class OrderTest {\n    @Test\n    void a() {\n        " + body + "\n    }\n\n"
                "    @Test\n    void b() {\n        // copied\n        " + body.replace("\n        ", "\n            ")
                + "\n    }\n}\n")
        got = scan({"src/test/java/x/OrderTest.java": java})
        self.assertEqual(got["duplicate-test-body"]["count"], 1)

    def test_trivial_bodies_are_not_reported(self):
        got = scan({"web/cart.test.ts": "it('a', () => { expect(add(1, 2)).toBe(3); });\n"
                                        "it('b', () => { expect(add(1, 2)).toBe(3); });\n"})
        self.assertNotIn("duplicate-test-body", got)

    def test_existing_checks_still_fire(self):
        got = scan({"tests/test_x.py": "import time\n\ndef test_wait():\n    time.sleep(2)\n    x = 1\n"})
        self.assertIn("fixed-sleep", got)
        self.assertIn("no-assertion", got)


if __name__ == "__main__":
    unittest.main()
