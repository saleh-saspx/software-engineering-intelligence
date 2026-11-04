#!/usr/bin/env bash
# Builds a deterministic git history in the target directory. The final working tree is
# byte-identical to the fixture files: only numeric constants change across commits.
set -eu
cd "${1:-.}"
OS=src/main/java/com/acme/shop/orders/OrderService.java
BC=src/main/java/com/acme/shop/billing/BillingClient.java
IC=src/main/java/com/acme/shop/billing/InvoiceCalculator.java
git init -q .
git symbolic-ref HEAD refs/heads/main
git config user.name "Alice Dev"; git config user.email alice@acme.test; git config commit.gpgsign false
commit() { # date name email message
  GIT_AUTHOR_DATE="$1T10:00:00+00:00" GIT_COMMITTER_DATE="$1T10:00:00+00:00" \
  GIT_AUTHOR_NAME="$2" GIT_AUTHOR_EMAIL="$3" GIT_COMMITTER_NAME="$2" GIT_COMMITTER_EMAIL="$3" \
  git commit -q -a -m "$4"
}
setc() { sed -i "s/$2 = [0-9.]*;/$2 = $3;/" "$1"; }
# initial state (May 2023)
setc $OS BULK_DISCOUNT_THRESHOLD 5; setc $OS BULK_DISCOUNT 0.05; setc $OS LOYALTY_DISCOUNT 0.02
setc $BC TIMEOUT_SECONDS 30; setc $IC TAX_RATE 0.16
git add -A
commit 2023-05-10 "Alice Dev" alice@acme.test "Initial import of shop backend"
setc $OS LOYALTY_DISCOUNT 0.025;      commit 2025-11-20 "Bob Dev" bob@acme.test "pricing: adjust loyalty discount"
setc $OS BULK_DISCOUNT_THRESHOLD 8;   commit 2025-12-15 "Carol Dev" carol@acme.test "pricing: bulk threshold to 8"
setc $BC TIMEOUT_SECONDS 20;          commit 2026-01-12 "Bob Dev" bob@acme.test "billing: lower timeout"
setc $OS BULK_DISCOUNT 0.06;          commit 2026-01-28 "Alice Dev" alice@acme.test "fix: bulk discount for wholesale accounts"
setc $OS LOYALTY_DISCOUNT 0.03;       commit 2026-02-17 "Carol Dev" carol@acme.test "fix: loyalty discount applied twice (hotfix)"
setc $OS BULK_DISCOUNT_THRESHOLD 12;  commit 2026-03-09 "Bob Dev" bob@acme.test "pricing: wholesale rule change"
setc $IC TAX_RATE 0.19;               commit 2026-04-02 "Alice Dev" alice@acme.test "billing: new VAT rate"
setc $OS BULK_DISCOUNT 0.08;          commit 2026-04-21 "Carol Dev" carol@acme.test "fix: rounding of discounted totals"
setc $OS BULK_DISCOUNT_THRESHOLD 10;  commit 2026-05-30 "Bob Dev" bob@acme.test "revert wholesale threshold"
setc $OS BULK_DISCOUNT 0.07;          commit 2026-06-18 "Alice Dev" alice@acme.test "hotfix: discount too high for small wholesale orders"
setc $BC TIMEOUT_SECONDS 10;          commit 2026-07-07 "Carol Dev" carol@acme.test "billing: fail faster"
setc $OS LOYALTY_DISCOUNT 0.035;      commit 2026-08-25 "Bob Dev" bob@acme.test "pricing: summer loyalty promo"
setc $OS LOYALTY_DISCOUNT 0.03;       commit 2026-09-15 "Bob Dev" bob@acme.test "fix: revert summer promo, customers double-discounted"
