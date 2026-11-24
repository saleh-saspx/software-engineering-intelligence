"""scripts/migration_lint.py: engine-specific checks; PostgreSQL and MySQL behaviour kept as in 1.2."""
import json
import unittest

from _support import Tree, run_script

import migration_lint


def checks(files, dialect="auto"):
    with Tree(files) as t:
        res = migration_lint.scan(t.path, None, dialect, None)
    return res, [(l["line"], l["check"], l["severity"]) for l in res["leads"]]


PG = """
CREATE INDEX idx_orders_customer ON orders (customer_id);
ALTER TABLE orders ADD COLUMN note text NOT NULL;
ALTER TABLE orders ALTER COLUMN amount TYPE numeric(18,2);
ALTER TABLE orders ADD CONSTRAINT fk_c FOREIGN KEY (customer_id) REFERENCES customers(id);
"""


class PostgresAndMysqlUnchanged(unittest.TestCase):
    def test_postgresql_checks(self):
        _, got = checks({"db/migrations/V2__a.sql": PG}, "postgresql")
        self.assertIn((1, "index-not-concurrent", "high"), got)
        self.assertIn((2, "add-not-null-without-default", "high"), got)
        self.assertIn((3, "alter-column-type", "high"), got)
        self.assertIn((4, "constraint-validated-under-lock", "medium"), got)
        self.assertIn((1, "no-lock-timeout", "info"), got, "points at the first DDL statement, even at the top of the file")

    def test_mysql_checks(self):
        _, got = checks({"db/migrations/V2__a.sql": PG}, "mysql")
        names = {c for _, c, _ in got}
        self.assertNotIn("index-not-concurrent", names)
        self.assertIn((3, "alter-column-type", "medium"), got)
        self.assertIn("mysql-online-ddl-unspecified", names)

    def test_mariadb_runs_mysql_checks(self):
        res_maria, maria = checks({"db/migrations/V2__a.sql": PG}, "mariadb")
        _, mysql = checks({"db/migrations/V2__a.sql": PG}, "mysql")
        self.assertEqual(maria, mysql)
        self.assertIn("MySQL checks", res_maria["dialect_default"])


class OtherEngines(unittest.TestCase):
    def test_oracle(self):
        sql = ("CREATE INDEX ix_a ON accounts (branch_code);\n"
               "CREATE INDEX ix_b ON accounts (owner_id) ONLINE;\n"
               "ALTER TABLE accounts ADD (risk_class VARCHAR2(10) NOT NULL);\n")
        _, got = checks({"db/migrations/V5__a.sql": sql}, "oracle")
        self.assertIn((1, "index-not-online", "high"), got)
        self.assertNotIn((2, "index-not-online", "high"), got)
        self.assertIn((3, "add-not-null-without-default", "high"), got)
        self.assertIn((2, "ddl-implicit-commit", "info"), got)
        self.assertNotIn("index-not-concurrent", {c for _, c, _ in got}, "PostgreSQL advice does not apply")

    def test_oracle_online_keyword_must_follow_the_column_list(self):
        sql = "CREATE INDEX users_online_idx ON users (online);\nCREATE INDEX ix2 ON users (seen) ONLINE;\n"
        _, got = checks({"db/migrations/V9__x.sql": sql}, "oracle")
        self.assertIn((1, "index-not-online", "high"), got)
        self.assertNotIn((2, "index-not-online", "high"), got)

    def test_sqlserver_with_go_batches(self):
        sql = ("CREATE NONCLUSTERED INDEX IX_P ON [dbo].[Payments] ([AccountId]);\nGO\n"
               "CREATE INDEX IX_ok ON dbo.Payments (Ref) WITH (ONLINE = ON);\nGO\n"
               "ALTER TABLE dbo.Payments ALTER COLUMN Amount DECIMAL(19,4) NOT NULL;\nGO\n"
               "EXEC sp_rename 'dbo.Payments.Ref', 'Reference', 'COLUMN';\nGO\n")
        _, got = checks({"db/migrations/V7__p.sql": sql}, "sqlserver")
        self.assertIn((1, "index-not-online", "high"), got)
        self.assertNotIn((3, "index-not-online", "high"), got)
        self.assertIn((5, "alter-column-type", "medium"), got)
        self.assertIn((7, "rename", "high"), got)
        self.assertIn((1, "no-lock-timeout", "info"), got)

    def test_sqlite_alter_limits(self):
        sql = ("ALTER TABLE wallets ALTER COLUMN balance TYPE INTEGER;\n"
               "ALTER TABLE wallets ADD COLUMN code TEXT UNIQUE;\n"
               "ALTER TABLE wallets ADD COLUMN note TEXT;\n"
               "ALTER TABLE wallets RENAME COLUMN a TO b;\n")
        _, got = checks({"db/migrations/003_w.sql": sql}, "sqlite")
        self.assertIn((1, "sqlite-alter-unsupported", "high"), got)
        self.assertIn((2, "sqlite-alter-unsupported", "high"), got)
        self.assertFalse([g for g in got if g[0] == 3], "plain ADD COLUMN is supported")
        self.assertIn((4, "rename", "high"), got)

    def test_auto_detection_needs_an_engine_only_construct(self):
        _, ora = checks({"db/migrations/V1__a.sql": "CREATE INDEX ix ON accounts (c);\n"
                                                    "ALTER TABLE accounts ADD (x VARCHAR2(10));\n"})
        self.assertIn("index-not-online", {c for _, c, _ in ora})
        _, ts = checks({"db/migrations/V1__a.sql": "CREATE INDEX ix ON accounts (c) TABLESPACE fast;\n"})
        self.assertIn("index-not-concurrent", {c for _, c, _ in ts},
                      "TABLESPACE alone (valid in PostgreSQL too) must not switch the file to Oracle")


class MysqlAdditions(unittest.TestCase):
    """1.3.0 adds two info-level MySQL leads; the MySQL leads and severities above are unchanged."""

    def test_raw_sql_lock_wait_timeout_and_implicit_commit(self):
        sql = ("ALTER TABLE payments ADD COLUMN note varchar(20) NULL, ALGORITHM=INSTANT;\n"
               "CREATE INDEX ix_m ON payments (merchant_id, created_at);\n")
        _, got = checks({"db/migrations/V7__p.sql": sql}, "mysql")
        self.assertIn((1, "no-lock-timeout", "info"), got)
        self.assertIn((2, "ddl-implicit-commit", "info"), got)
        _, pg = checks({"db/migrations/V7__p.sql": sql}, "postgresql")
        self.assertNotIn("ddl-implicit-commit", {c for _, c, _ in pg}, "PostgreSQL DDL is transactional")

    def test_metadata_lock_timeout_suppresses_the_lead_but_the_row_lock_timeout_does_not(self):
        sql = "SET SESSION lock_wait_timeout = 5;\nALTER TABLE payments ADD COLUMN n int NULL, ALGORITHM=INSTANT;\n"
        _, got = checks({"db/migrations/V8__p.sql": sql}, "mysql")
        self.assertNotIn("no-lock-timeout", {c for _, c, _ in got})
        _, row = checks({"db/migrations/V8__p.sql": sql.replace("lock_wait_timeout", "innodb_lock_wait_timeout")}, "mysql")
        self.assertIn((2, "no-lock-timeout", "info"), row)

    def test_a_new_table_needs_no_lock_timeout(self):
        sql = "CREATE TABLE t (id bigint PRIMARY KEY);\nCREATE INDEX ix_t ON t (id);\n"
        _, got = checks({"db/migrations/V10__t.sql": sql}, "mysql")
        names = {c for _, c, _ in got}
        self.assertNotIn("no-lock-timeout", names)
        self.assertIn("ddl-implicit-commit", names)

    def test_laravel_migration_on_mysql(self):
        php = ("<?php\nuse Illuminate\\Database\\Migrations\\Migration;\nuse Illuminate\\Database\\Schema\\Blueprint;\n"
               "use Illuminate\\Support\\Facades\\Schema;\nreturn new class extends Migration {\n"
               "    public function up(): void\n    {\n%s"
               "        Schema::table('payments', function (Blueprint $table) {\n"
               "            $table->decimal('amount', 19, 4)->change();\n        });\n    }\n};\n")
        _, got = checks({"database/migrations/2026_01_01_000000_w.php": php % ""}, "mysql")
        change_line = [ln for ln, c, _ in got if c == "alter-column-type"][0]
        self.assertIn((change_line, "no-lock-timeout", "info"), got)
        guarded = php % "        DB::statement('SET SESSION lock_wait_timeout = 5');\n"
        _, got2 = checks({"database/migrations/2026_01_01_000000_w.php": guarded}, "mysql")
        self.assertNotIn("no-lock-timeout", {c for _, c, _ in got2})


class PathHandling(unittest.TestCase):
    def test_the_migrations_folder_itself_and_explicit_files(self):
        with Tree({"db/migrations/001_expand.sql": "ALTER TABLE orders ADD COLUMN note text;\n",
                   "scratch/migrations/002_index.sql": "CREATE INDEX ix_o ON orders (customer_id);\n",
                   "notes/change.sql": "CREATE INDEX ix_o ON orders (customer_id);\n",
                   "notes/readme.php": "<?php echo 'x';\n"}) as t:
            self.assertEqual(migration_lint.scan(t.path / "db" / "migrations", None, "postgresql", None)["files_analysed"], 1)
            self.assertEqual(migration_lint.scan(t.path / "scratch" / "migrations", None, "postgresql", None)["files_analysed"], 1)
            self.assertEqual(migration_lint.scan(t.path / "notes", None, "postgresql", None)["files_analysed"], 0,
                             "an ordinary folder is not treated as migrations")
            named = migration_lint.scan(t.path, ["notes/change.sql", "notes/readme.php"], "postgresql", None)
            self.assertEqual(named["files_analysed"], 1, "a SQL file named explicitly is analysed wherever it lives")
            self.assertEqual(named["not_analysed"], ["notes/readme.php"])
            one = run_script("migration_lint.py", str(t.path / "notes" / "change.sql"), "--dialect", "postgresql", "--json")
            self.assertEqual(one.returncode, 0, one.stderr)
            self.assertIn("index-not-concurrent", {l["check"] for l in json.loads(one.stdout)["leads"]})
        self.assertEqual(run_script("migration_lint.py", "/nonexistent-path").returncode, 2)


class Cli(unittest.TestCase):
    def test_dialect_choices(self):
        with Tree({"db/migrations/V1__a.sql": "CREATE INDEX ix ON t (c);\n"}) as t:
            for d in ("oracle", "sqlserver", "sqlite", "mariadb"):
                res = run_script("migration_lint.py", str(t.path), "--dialect", d)
                self.assertEqual(res.returncode, 0, res.stderr)
            gate = run_script("migration_lint.py", str(t.path), "--dialect", "oracle", "--fail-on", "high")
            self.assertEqual(gate.returncode, 1)


if __name__ == "__main__":
    unittest.main()
