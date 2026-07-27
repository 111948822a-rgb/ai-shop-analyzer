import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import init_db
from app.models import standard


def main():
    print("Initializing database tables...")
    init_db()
    print("Database tables created successfully!")


if __name__ == "__main__":
    main()