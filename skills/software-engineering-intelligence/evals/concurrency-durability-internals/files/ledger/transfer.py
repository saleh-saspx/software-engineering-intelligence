def transfer(conn, from_id, to_id, amount):
    with conn.transaction():
        conn.execute("SELECT balance FROM accounts WHERE id = %s FOR UPDATE", [from_id])
        conn.execute("SELECT balance FROM accounts WHERE id = %s FOR UPDATE", [to_id])
        conn.execute("UPDATE accounts SET balance = balance - %s WHERE id = %s", [amount, from_id])
        conn.execute("UPDATE accounts SET balance = balance + %s WHERE id = %s", [amount, to_id])
        conn.execute("INSERT INTO postings (account_id, amount) VALUES (%s, %s), (%s, %s)",
                     [from_id, -amount, to_id, amount])
