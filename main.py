from flask import Flask, request, jsonify
import oracledb
import logging
import requests
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
import glob
import os
import atexit
import signal
import sys

app = Flask(__name__)

# 로그 파일 롤링: 하루마다 event.log.YYmmdd로 저장, 30일 보관
class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    def doRollover(self):
        super().doRollover()
        # 롤링 후 30개(30일) 초과 파일 삭제
        log_files = sorted(glob.glob('logs/event.log.*'))
        if len(log_files) > 30:
            for old_file in log_files[:-30]:
                try:
                    os.remove(old_file)
                except Exception as e:
                    logging.error(f"logFile delete Failed: {old_file} - {e}")

handler = CustomTimedRotatingFileHandler(
    'logs/event.log', when='midnight', interval=1, backupCount=30, encoding='utf-8', utc=False
)
handler.suffix = "%y%m%d"
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logging.getLogger().handlers = [handler]
logging.getLogger().setLevel(logging.INFO)


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        logging.info(f"/webhook received: {data}")
        if not data:
            logging.error("Invalid JSON: Empty Data.")
            return jsonify({'error': 'Invalid JSON'}), 400
    except Exception as e:
        logging.exception("JSON Parsing Error:")
        return jsonify({'error': str(e)}), 500

    try:
        # 1. 멤버 정보 API 호출
        pcode = data.get("pcode")
        url = f"https://141.164.62.222:8080/open/api/json/project/{pcode}/members"
        headers = {"x-whatap-token": "MMRXIOJH9VLYUZNT03ZL"}
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()
        members = response.json().get("data", [])
        
        # 2. sms 값이 있는 멤버만 추출
        phone_numbers = [m["sms"] for m in members if m.get("sms")]
        
        # 3. 각 전화번호마다 INSERT
        conn = oracledb.connect(
          user="whatap",
          password="whatap!234",
          dsn=oracledb.makedsn("158.247.242.124", 1521, sid="ORA")
        )
        cursor = conn.cursor()

        sql = """
        INSERT INTO EM_TRAN (
            TRAN_PR, TRAN_PHONE, TRAN_CALLBACK, TRAN_STATUS, TRAN_DATE, TRAN_MSG, TRAN_TYPE
        ) VALUES (
            em_tran_pr.nextval, :TRAN_PHONE, :TRAN_CALLBACK, :TRAN_STATUS, :TRAN_DATE, :TRAN_MSG, :TRAN_TYPE
        )
        """

        for phone in phone_numbers:
            cursor.execute(sql, {
                "TRAN_PHONE": phone,
                "TRAN_CALLBACK": "15882323",
                "TRAN_STATUS": "1",
                "TRAN_DATE": datetime.now(),
                "TRAN_MSG": data.get("message"),
                "TRAN_TYPE": 4
            })

        conn.commit()
        return jsonify({'status': 'success', 'inserted': len(phone_numbers)}), 200

    except requests.RequestException as e:
        logging.exception("OpenAPI Call Error:")
        return jsonify({'error': str(e)}), 500
    except oracledb.DatabaseError as e:
        logging.exception("Database Error:")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logging.exception("Unknown Error:")
        return jsonify({'error': str(e)}), 500

    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def on_exit():
    logging.info("Webhook process has successfully terminated.")

def handle_sigterm(signum, frame):
    logging.info(f"Webhook process is terminated by SIGNAL({signum})")
    sys.exit(0)

atexit.register(on_exit)
signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
