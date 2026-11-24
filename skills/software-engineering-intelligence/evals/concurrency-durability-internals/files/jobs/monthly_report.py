def run(conn):
    conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
    for account in conn.execute("SELECT id FROM accounts"):
        rows = conn.execute("SELECT * FROM postings WHERE account_id = %s", [account.id])
        write_report_section(account, rows)       # about 3 hours in total
    conn.execute("COMMIT")
