"""scripts/_db.py and the databases section of scripts/repo_survey.py."""
import json
import unittest

from _support import Tree, run_script

import _db


class DetectDatabases(unittest.TestCase):
    def test_empty_repository_is_unknown(self):
        with Tree({"README.md": "# x\n"}) as t:
            db = _db.detect_databases(t.path)
        self.assertEqual(db["status"], "UNKNOWN")
        self.assertEqual(db["application_engines"], [])
        self.assertIn("UNKNOWN", db["notes"][0])

    def test_application_engine_from_config_and_version_from_compose(self):
        with Tree({
            "src/main/resources/application.properties": "spring.datasource.url=jdbc:oracle:thin:@//db:1521/FREEPDB1\n",
            "docker-compose.yml": "services:\n  db:\n    image: gvenzl/oracle-free:23-slim\n",
        }) as t:
            db = _db.detect_databases(t.path)
        self.assertEqual(db["status"], "detected")
        self.assertEqual(db["application_engines"], ["oracle"])
        self.assertIn("23-slim", db["versions"].get("oracle", []))

    def test_stand_in_for_tests_is_reported(self):
        with Tree({
            "pom.xml": """
                <project><dependencies>
                  <dependency><groupId>com.oracle.database.jdbc</groupId><artifactId>ojdbc11</artifactId></dependency>
                  <dependency><groupId>com.h2database</groupId><artifactId>h2</artifactId><scope>test</scope></dependency>
                </dependencies></project>
            """,
        }) as t:
            db = _db.detect_databases(t.path)
        self.assertEqual(db["application_engines"], ["oracle"], "a test-scoped H2 dependency is not an application engine")
        self.assertIn("h2", db["test_engines"])
        self.assertTrue(any("TEST-DATA-02" in n for n in db["notes"]))

    def test_rails_database_yml_sections(self):
        with Tree({"config/database.yml": """
            default: &default
              pool: 5
            development:
              adapter: postgresql
            test:
              adapter: sqlite3
            production:
              adapter: postgresql
        """}) as t:
            db = _db.detect_databases(t.path)
        self.assertEqual(db["application_engines"], ["postgresql"])
        self.assertEqual(db["test_engines"], ["sqlite"])
        self.assertTrue(any("SQLite" in n for n in db["notes"]))

    def test_laravel_database_php_lists_drivers_but_only_the_default_counts(self):
        config = """<?php
            return [
                'default' => env('DB_CONNECTION', 'sqlite'),
                'connections' => [
                    'sqlite' => ['driver' => 'sqlite'],
                    'mysql' => ['driver' => 'mysql'],
                    'pgsql' => ['driver' => 'pgsql'],
                    'sqlsrv' => ['driver' => 'sqlsrv'],
                ],
            ];
        """
        with Tree({"config/database.php": config}) as t:
            self.assertEqual(_db.detect_databases(t.path)["application_engines"], ["sqlite"])
        with Tree({"config/database.php": config, ".env.example": "DB_CONNECTION=mysql\n"}) as t:
            self.assertEqual(_db.detect_databases(t.path)["application_engines"], ["mysql"],
                             "the framework fallback does not compete with the configured engine")

    def test_sample_and_fixture_projects_are_not_this_application(self):
        with Tree({"requirements.txt": "psycopg[binary]==3.2\npsycopg2==2.9\n",
                   "examples/legacy-app/config/database.yml": "production:\n  adapter: mysql2\n",
                   "tests/fixtures/oracle/application.properties": "spring.datasource.url=jdbc:oracle:thin:@//x/y\n"}) as t:
            db = _db.detect_databases(t.path)
        self.assertEqual(db["application_engines"], ["postgresql"])
        self.assertNotIn("oracle", db["engines"])
        self.assertNotIn("mysql", db["engines"])

    def test_development_dependencies_are_test_engines(self):
        files = {
            "package.json": '{"dependencies": {"pg": "^8"}, "devDependencies": {"sqlite3": "^5"}}',
            "composer.json": '{"require": {"php": "^8.3"}, "require-dev": {"ext-pdo_sqlite": "*"}}',
            "pyproject.toml": '[project]\ndependencies = ["psycopg>=3"]\n[project.optional-dependencies]\n'
                              'test = [\n  "pytest",\n  "aiosqlite",\n]\n',
            "Gemfile": "gem 'pg'\ngroup :development, :test do\n  gem 'sqlite3'\nend\n",
        }
        with Tree(files) as t:
            db = _db.detect_databases(t.path)
        self.assertEqual(db["application_engines"], ["postgresql"])
        self.assertIn("sqlite", db["test_engines"])

    def test_constructs_shared_by_engines(self):
        self.assertEqual(_db.construct_engines("postgresql", "ON CONFLICT upsert"), {"postgresql", "sqlite"})
        self.assertEqual(_db.dialect_hints("engine = Memory('/tmp')", code=True), {})
        self.assertEqual(_db.dialect_hints("log('retry on conflict with peer')", code=True), {})

    def test_mariadb_is_not_double_counted_as_mysql(self):
        with Tree({".env.example": "DB_CONNECTION=mariadb\nDATABASE_URL=mariadb://app@db/app\n"}) as t:
            db = _db.detect_databases(t.path)
        self.assertEqual(db["application_engines"], ["mariadb"])

    def test_secret_values_are_not_reported(self):
        with Tree({".env": "DATABASE_URL=postgres://admin:S3cr3tPassw0rd@db:5432/app\n"}) as t:
            db = _db.detect_databases(t.path)
        dump = json.dumps(db)
        self.assertNotIn("S3cr3tPassw0rd", dump)
        self.assertEqual(db["application_engines"], ["postgresql"])


class DialectHints(unittest.TestCase):
    def test_engine_constructs(self):
        self.assertIn("postgresql", _db.dialect_hints("INSERT INTO t VALUES (1) ON CONFLICT (id) DO NOTHING"))
        self.assertIn("mysql", _db.dialect_hints("INSERT INTO t VALUES (1) ON DUPLICATE KEY UPDATE n = n + 1"))
        self.assertIn("oracle", _db.dialect_hints("SELECT NVL(a, 0) FROM t WHERE ROWNUM <= 10"))
        self.assertIn("sqlserver", _db.dialect_hints("SELECT TOP 10 * FROM t WITH (NOLOCK)"))
        self.assertIn("sqlite", _db.dialect_hints("INSERT OR REPLACE INTO t VALUES (1)"))
        self.assertEqual(_db.dialect_hints("SELECT a, b FROM t WHERE a = ?"), {})

    def test_code_mode_ignores_comments_and_lower_case_words(self):
        code = (
            "engine = create_engine(url)  # runs concurrently, top 10 customers\n"
            "data = raw.decode('utf-8'); n = Number(x)  # pragma: no cover\n"
            "id = Column(Integer, autoincrement=True)\n"
            "rows = DB::table('users')->get();\n"
        )
        self.assertEqual(_db.dialect_hints(code, code=True), {})
        self.assertIn("postgresql", _db.dialect_hints("q = 'SELECT x::text FROM t'", code=True))

    def test_dominant_dialect(self):
        self.assertEqual(_db.dominant_dialect("CREATE TABLE a (id NUMBER(19), n VARCHAR2(10))"), "oracle")
        self.assertIsNone(_db.dominant_dialect("CREATE TABLE a (id int)"))


class RepoSurveyDatabases(unittest.TestCase):
    def test_engines_in_a_ci_build_matrix_are_test_engines(self):
        ci = ("jobs:\n  test:\n    strategy:\n      matrix:\n        db: [postgres:16, mysql:8.0, sqlite]\n"
              "    services:\n      mssql:\n        image: mcr.microsoft.com/mssql/server:2022-latest\n")
        with Tree({".github/workflows/ci.yml": ci, "README.md": "Runs on postgres:16 in production.\n"}) as t:
            db = _db.detect_databases(t.path)
        self.assertEqual(db["application_engines"], [], "a CI matrix says which engines tests use, not production")
        self.assertEqual(db["test_engines"], ["mysql", "postgresql", "sqlserver"])
        self.assertEqual(db["versions"]["postgresql"], ["16"])
        self.assertEqual(db["versions"]["mysql"], ["8.0"])
        with Tree({".github/workflows/ci.yml": "env:\n  URL: postgresql://postgres:secret@localhost/app\n"}) as t:
            db = _db.detect_databases(t.path)
        self.assertNotIn("secret", json.dumps(db), "a credential after postgres: is not an image tag")

    def test_survey_includes_databases(self):
        with Tree({"requirements.txt": "psycopg2-binary==2.9\n", "app/main.py": "print('x')\n"}) as t:
            res = run_script("repo_survey.py", str(t.path), "--json")
            self.assertEqual(res.returncode, 0, res.stderr)
            data = json.loads(res.stdout)
            self.assertEqual(data["databases"]["application_engines"], ["postgresql"])
            md = run_script("repo_survey.py", str(t.path))
            self.assertIn("## Databases", md.stdout)


if __name__ == "__main__":
    unittest.main()
