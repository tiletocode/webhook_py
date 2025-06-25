import oracledb
import logging

def select_recent_em_tran(limit=10):
    try:
        conn = oracledb.connect(
            user="whatap",
            password="whatap!234",
            dsn=oracledb.makedsn("158.247.242.124", 1521, sid="ORA")
        )
        cursor = conn.cursor()
        sql = """
        SELECT TRAN_PR, TRAN_PHONE, TRAN_CALLBACK, TRAN_STATUS, TRAN_DATE, TRAN_MSG, TRAN_TYPE
        FROM (
            SELECT *
            FROM EM_TRAN
            ORDER BY TRAN_PR DESC
        )
        WHERE ROWNUM <= :limit
        """
        cursor.execute(sql, {"limit": limit})
        rows = cursor.fetchall()
        for row in rows:
            print(row)
        return rows
    except oracledb.DatabaseError as e:
        logging.exception("Database Error:")
        return []
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    select_recent_em_tran(10)
