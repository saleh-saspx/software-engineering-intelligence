import os

SPLIT_PAYMENTS_ENABLED = os.getenv("SPLIT_PAYMENTS_ENABLED", "false").lower() == "true"
