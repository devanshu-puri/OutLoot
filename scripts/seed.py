#!/usr/bin/env python3
"""
Seed script to initialize item definitions and rewards in the SQLite database.
"""
from server.db import get_db, init_db, tx
from server.services.items import seed_item_definitions_if_empty
from server.services.market import seed_rewards_if_empty


def run_seed():
    print("Initializing database...")
    init_db()
    with get_db() as conn:
        with tx(conn):
            seed_item_definitions_if_empty(conn)
            seed_rewards_if_empty(conn)
    print("Database successfully seeded with item definitions and sample rewards!")


if __name__ == "__main__":
    run_seed()
