import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.init_db import init_database

if __name__ == "__main__":
    print("Resetting and seeding Hospital Resource Optimizer database...")
    init_database(drop_existing=True)
    print("Database seeding complete.")
