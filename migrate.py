from models import Base
from database import engine

# This script will create all tables defined in models.py
if __name__ == "__main__":
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
