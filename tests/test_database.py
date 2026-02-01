import sqlite3
import os
import sys


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

DB_PATH = "settings_test.db"

def test_database_insert():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO contracts (buyer_json, seller_json, buyer_id, contract_number, file_path)
        VALUES ('{"name":"Ali","lname":"Test"}',
                '{"name":"Reza","lname":"Test"}',
                '1234567890',
                '99999',
                'test.docx')
    """)

    conn.commit()

    cur.execute("SELECT * FROM contracts WHERE contract_number = '99999'")
    row = cur.fetchone()

    conn.close()

    assert row is not None

def test_contract_number_unique():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # یک قرارداد تستی
    cur.execute("""
        INSERT INTO contracts (buyer_json, seller_json, buyer_id, contract_number, file_path)
        VALUES ('{"name":"Ali"}', '{"name":"Reza"}', '111', '5000', 'a.docx')
    """)
    conn.commit()

    # دوباره همان شماره قرارداد
    try:
        cur.execute("""
            INSERT INTO contracts (buyer_json, seller_json, buyer_id, contract_number, file_path)
            VALUES ('{"name":"Ali2"}', '{"name":"Reza2"}', '222', '5000', 'b.docx')
        """)
        conn.commit()
        assert False, "باید خطا می‌داد ولی نداد"
    except sqlite3.IntegrityError:
        assert True