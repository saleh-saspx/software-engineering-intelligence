"""scripts/schema_lint.py: data-type, key and relationship leads across engines and frameworks."""
import json
import unittest

from _support import Tree, run_script

import schema_lint


def leads(files, dialect="auto"):
    with Tree(files) as t:
        res = schema_lint.scan(t.path, None, dialect, 50)
    return res, {(l["check"], l["table"], l["column"].lower()): l for l in res["leads"]}


class Types(unittest.TestCase):
    def test_money_in_binary_float_is_high(self):
        _, got = leads({"db/schema.sql": "CREATE TABLE payments (id bigint PRIMARY KEY, amount double precision);"},
                       "postgresql")
        self.assertEqual(got[("money-float", "payments", "amount")]["severity"], "high")

    def test_decimal_without_scale_depends_on_engine(self):
        ddl = "CREATE TABLE loans (id bigint PRIMARY KEY, principal DECIMAL NOT NULL);"
        _, my = leads({"s.sql": ddl}, "mysql")
        _, ms = leads({"s.sql": ddl}, "sqlserver")
        _, pg = leads({"s.sql": ddl}, "postgresql")
        self.assertEqual(my[("decimal-without-scale", "loans", "principal")]["severity"], "high")
        self.assertIn("(10,0)", my[("decimal-without-scale", "loans", "principal")]["message"])
        self.assertIn("(18,0)", ms[("decimal-without-scale", "loans", "principal")]["message"])
        self.assertEqual(pg[("decimal-without-scale", "loans", "principal")]["severity"], "medium")

    def test_oracle_float_is_decimal_not_ieee(self):
        _, got = leads({"s.sql": "CREATE TABLE r (id NUMBER(19) PRIMARY KEY, interest_rate FLOAT);"}, "oracle")
        self.assertNotIn(("rate-float", "r", "interest_rate"), got)
        self.assertIn(("decimal-without-scale", "r", "interest_rate"), got)

    def test_oracle_decimal_and_numeric_default_to_scale_zero(self):
        _, got = leads({"s.sql": "CREATE TABLE l (id NUMBER(19) PRIMARY KEY, principal DECIMAL, fee_amount NUMERIC, "
                                 "amount NUMBER);"}, "oracle")
        self.assertEqual(got[("decimal-without-scale", "l", "principal")]["severity"], "high")
        self.assertIn("scale 0", got[("decimal-without-scale", "l", "fee_amount")]["message"])
        self.assertEqual(got[("decimal-without-scale", "l", "amount")]["severity"], "medium")

    def test_measurements_and_flags_are_not_money_or_identifiers(self):
        _, got = leads({"s.sql": "CREATE TABLE t (id bigint PRIMARY KEY, speed_limit real, total_distance double precision, "
                                 "battery_charge float, credit_score float, credit_limit float, phone_verified smallint);"},
                       "postgresql")
        flagged = {k[2] for k in got if k[0] == "money-float"}
        self.assertEqual(flagged, {"credit_limit"})
        self.assertNotIn(("identifier-numeric", "t", "phone_verified"), got)

    def test_orm_columns_are_judged_by_the_type_the_orm_generates(self):
        files = {"prisma/schema.prisma": 'datasource db { provider = "mysql" }\nmodel Card {\n  id Int @id\n'
                                          '  expiresAt DateTime\n  renewAt DateTime @db.Timestamp(0)\n}\n',
                 "src/main/java/x/Loan.java": "@Entity\npublic class Loan {\n    @EmbeddedId\n    private LoanKey key;\n"
                                              "    private BigDecimal amount;\n    private java.util.Date maturesOn;\n}\n"}
        _, got = leads(files, "mysql")
        self.assertNotIn(("mysql-timestamp-range", "card", "expiresat"), got, "Prisma DateTime is DATETIME(3) on MySQL")
        self.assertIn(("mysql-timestamp-range", "card", "renewat"), got)
        self.assertNotIn(("decimal-without-scale", "loan", "amount"), got, "the JPA provider chooses precision and scale")
        self.assertIn(("framework-default-precision", "loan", "amount"), got)
        self.assertNotIn(("no-primary-key", "loan", ""), got)
        self.assertFalse([k for k in got if k[0] == "mysql-timestamp-range" and k[1] == "loan"])

    def test_sqlite_ignores_declared_precision(self):
        _, got = leads({"s.sql": "CREATE TABLE w (id INTEGER PRIMARY KEY, balance DECIMAL(12,2));"}, "sqlite")
        self.assertIn(("sqlite-numeric-affinity", "w", "balance"), got)

    def test_identifiers_in_numeric_types(self):
        _, got = leads({"s.sql": "CREATE TABLE a (id bigint PRIMARY KEY, account_number bigint, phone integer, "
                                 "branch_code numeric(4));"}, "postgresql")
        for col in ("account_number", "phone", "branch_code"):
            self.assertIn(("identifier-numeric", "a", col), got)

    def test_exchange_rate_scale(self):
        _, got = leads({"s.sql": "CREATE TABLE q (id bigint PRIMARY KEY, fx_rate numeric(12,4));"}, "postgresql")
        self.assertIn(("small-scale-rate", "q", "fx_rate"), got)

    def test_time_types(self):
        _, pg = leads({"s.sql": "CREATE TABLE e (id bigint PRIMARY KEY, created_at timestamp, "
                                "occurred_at timestamp with time zone, birth_date timestamp);"}, "postgresql")
        self.assertIn(("timestamp-without-zone", "e", "created_at"), pg)
        self.assertNotIn(("timestamp-without-zone", "e", "occurred_at"), pg)
        self.assertIn(("date-as-timestamp", "e", "birth_date"), pg)
        _, my = leads({"s.sql": "CREATE TABLE l (id bigint PRIMARY KEY, maturity_at TIMESTAMP, created_at TIMESTAMP);"},
                      "mysql")
        self.assertEqual(my[("mysql-timestamp-range", "l", "maturity_at")]["severity"], "high")
        self.assertEqual(my[("mysql-timestamp-range", "l", "created_at")]["severity"], "info")
        _, ms = leads({"s.sql": "CREATE TABLE [dbo].[P] ([Id] INT PRIMARY KEY, [CreatedAt] DATETIME NOT NULL)"},
                      "sqlserver")
        self.assertIn(("sqlserver-datetime", "p", "createdat"), ms)


class Structure(unittest.TestCase):
    def test_keys_and_relationships(self):
        ddl = """
            CREATE TABLE customers (id bigint PRIMARY KEY, phone1 varchar(20), phone2 varchar(20));
            CREATE TABLE accounts (
              id bigint PRIMARY KEY,
              customer_id bigint NOT NULL REFERENCES customers(id),
              owner_type varchar(50), owner_id bigint,
              item_ids text,
              status varchar(20) NOT NULL
            );
            CREATE TABLE notes (body text);
            CREATE TABLE transfers (id bigint PRIMARY KEY, account_id bigint, trace_id varchar(64));
        """
        _, pg = leads({"s.sql": ddl}, "postgresql")
        self.assertIn(("fk-without-index", "accounts", "customer_id"), pg)
        self.assertIn(("polymorphic-reference", "accounts", "owner_id"), pg)
        self.assertIn(("id-list-column", "accounts", "item_ids"), pg)
        self.assertIn(("status-free-text", "accounts", "status"), pg)
        self.assertIn(("no-primary-key", "notes", ""), pg)
        self.assertIn(("repeating-group", "customers", "phone1"), pg)
        self.assertIn(("missing-fk", "transfers", "account_id"), pg)
        self.assertNotIn(("missing-fk", "transfers", "trace_id"), pg, "trace IDs point outside the schema")
        _, my = leads({"s.sql": ddl}, "mysql")
        self.assertNotIn(("fk-without-index", "accounts", "customer_id"), my, "InnoDB indexes foreign keys itself")

    def test_structure_false_positives(self):
        ddl = """
            CREATE TABLE payments (id bigint PRIMARY KEY);
            CREATE TABLE c (id bigint PRIMARY KEY, iso2 char(2), iso3 char(3), x1 int, x2 int, ipv4 varchar(15),
                            ipv6 varchar(45), payment_type varchar(20), payment_id bigint REFERENCES payments(id),
                            CONSTRAINT ix UNIQUE (payment_id));
        """
        _, got = leads({"s.sql": ddl}, "postgresql")
        self.assertFalse([k for k in got if k[0] in ("repeating-group", "polymorphic-reference")])

    def test_check_constraint_and_index_silence_leads(self):
        ddl = """
            CREATE TABLE customers (id bigint PRIMARY KEY);
            CREATE TABLE orders (
              id bigint PRIMARY KEY,
              customer_id bigint NOT NULL REFERENCES customers(id),
              status varchar(20) NOT NULL CHECK (status IN ('new', 'paid')),
              total numeric(14,2) NOT NULL,
              created_at timestamptz NOT NULL
            );
            CREATE INDEX orders_customer_idx ON orders (customer_id, created_at);
        """
        res, _ = leads({"s.sql": ddl}, "postgresql")
        self.assertEqual(res["leads"], [], "a well-typed schema produces no leads")

    def test_ignore_marker(self):
        _, got = leads({"s.sql": "CREATE TABLE p (\n  id bigint PRIMARY KEY,\n"
                                 "  amount float -- schema_lint: ignore\n);"}, "postgresql")
        self.assertNotIn(("money-float", "p", "amount"), got)


class Frameworks(unittest.TestCase):
    def test_laravel_django_prisma_jpa_sqlalchemy(self):
        files = {
            "database/migrations/2024_01_01_000000_create_payments_table.php": """
                <?php
                return new class extends Migration {
                    public function up(): void {
                        Schema::create('payments', function (Blueprint $table) {
                            $table->id();
                            $table->decimal('amount');
                            $table->float('fee');
                            $table->timestamps();
                        });
                    }
                };
            """,
            "app/models.py": """
                from django.db import models

                class Invoice(models.Model):
                    total = models.FloatField()
                    note = models.CharField(max_length=200, null=True)
            """,
            "prisma/schema.prisma": """
                model Order {
                  id    Int   @id
                  price Float
                }
            """,
            "src/main/java/x/Transfer.java": """
                @Entity
                public class Transfer {
                    @Id
                    private Long id;
                    private double amount;
                }
            """,
            "py/tables.py": """
                class Ledger(Base):
                    __tablename__ = "ledger_entries"
                    id = Column(Integer, primary_key=True)
                    amount = Column(Float)
            """,
        }
        res, got = leads(files, "postgresql")
        self.assertIn(("framework-default-precision", "payments", "amount"), got)
        self.assertIn(("money-float", "payments", "fee"), got)
        self.assertIn(("money-float", "invoice", "total"), got)
        self.assertIn(("two-empty-values", "invoice", "note"), got)
        self.assertIn(("money-float", "order", "price"), got)
        self.assertIn(("money-float", "transfer", "amount"), got)
        self.assertIn(("money-float", "ledger_entries", "amount"), got)
        self.assertNotIn(("timestamp-without-zone", "payments", "created_at"), got,
                         "framework-managed timestamps are not reported one by one")
        self.assertEqual(set(res["files_parsed"]), {"laravel", "python", "prisma", "jpa"})

    def test_auto_dialect_per_file_when_repository_engine_unknown(self):
        files = {"a/mysql.sql": "CREATE TABLE l (id BIGINT AUTO_INCREMENT PRIMARY KEY, principal DECIMAL) ENGINE=InnoDB;",
                 "b/pg.sql": "CREATE TABLE m (id bigserial PRIMARY KEY, principal numeric, d jsonb);"}
        res, got = leads(files)
        self.assertIn(res["dialect_source"], ("SQL constructs, per file", "not determined"))
        self.assertEqual(got[("decimal-without-scale", "l", "principal")]["severity"], "high")
        self.assertEqual(got[("decimal-without-scale", "m", "principal")]["severity"], "medium")


class Cli(unittest.TestCase):
    def test_cli(self):
        with Tree({"s.sql": "CREATE TABLE p (id bigint PRIMARY KEY, amount real);"}) as t:
            md = run_script("schema_lint.py", str(t.path))
            self.assertEqual(md.returncode, 0, md.stderr)
            self.assertIn("LEADS", md.stdout)
            js = run_script("schema_lint.py", str(t.path), "--json", "--dialect", "postgresql")
            self.assertEqual(json.loads(js.stdout)["counts"].get("money-float"), 1)
        self.assertEqual(run_script("schema_lint.py", "/nonexistent-dir").returncode, 2)

    def test_a_single_file_and_calendar_date_advice(self):
        with Tree({"database/schema.sql": "CREATE TABLE cards (id bigint PRIMARY KEY, card_expires_at TIMESTAMP NULL);"}) as t:
            js = run_script("schema_lint.py", str(t.path / "database" / "schema.sql"), "--dialect", "mysql", "--json")
        self.assertEqual(js.returncode, 0, js.stderr)
        lead = [l for l in json.loads(js.stdout)["leads"] if l["check"] == "mysql-timestamp-range"][0]
        self.assertEqual(lead["severity"], "high")
        self.assertIn("DATE if the value is a calendar date", lead["fix"])


if __name__ == "__main__":
    unittest.main()
