import database
from sqlalchemy import text

def check_table_counts():
    engine = database.engine
    with engine.connect() as conn:
        fnol_count = conn.execute(text("SELECT COUNT(*) FROM fnol_work_items")).scalar()
        attachment_count = conn.execute(text("SELECT COUNT(*) FROM attachments")).scalar()
        print(f"FNOL Work Items: {fnol_count}")
        print(f"Attachments: {attachment_count}")

if __name__ == '__main__':
    check_table_counts()
