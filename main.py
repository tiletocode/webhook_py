from flask import Flask, request, jsonify
import oracledb
import logging
import requests
import atexit
import signal
import sys
from datetime import datetime
from lock_manager import is_request_processed, mark_request_completed
from logger_config import setup_logging

app = Flask(__name__)

# 로깅 설정 초기화
setup_logging()

@app.route('/webhook', methods=['POST'])
@app.route('/webhook/<groupId>', methods=['POST'])
def webhook_unified(groupId=None):
    try:
        data = request.get_json()
        log_id = f"groupId={groupId}" if groupId else "project"
        
        # UUID 중복 처리 방지 (파일 기반)
        request_uuid = data.get("uuid") if data else None
        if request_uuid:
            if is_request_processed(request_uuid):
                logging.info(f"Duplicate request ignored: uuid={request_uuid}")
                return jsonify({'status': 'duplicate', 'message': 'Request already processed'}), 200
        
        logging.info(f"/webhook received: {log_id}, uuid={request_uuid}, data={data}")
        if not data:
            logging.error("Invalid JSON: Empty Data.")
            return jsonify({'error': 'Invalid JSON'}), 400
    except Exception as e:
        logging.exception("JSON Parsing Error:")
        return jsonify({'error': str(e)}), 500

    try:
        # 1. 멤버 정보 API 호출
        all_members = []
        
        if groupId:
            # 그룹 멤버 API 호출
            # token: ACCOUNT API Key: admin@whatap.io
            group_url = f"https://141.164.62.222:8080/open/api/json/group/{groupId}/members"
            headers = {"x-whatap-token": "ZXFQ1QN2WZKQCXI1B5T6"}
            
            try:
                response = requests.get(group_url, headers=headers, verify=False)
                response.raise_for_status()
                json_resp = response.json()
                if "data" in json_resp and json_resp["data"] is not None:
                    all_members.extend(json_resp["data"])
                    logging.info(f"Group API returned {len(json_resp['data'])} members")
                else:
                    logging.warning(f"Group API response missing or null 'data' field: {json_resp}")
            except requests.RequestException as e:
                logging.warning(f"Group API call failed: {e}")
            
            # 프로젝트 멤버 API 호출
            pcode = data.get("pcode")
            if pcode:
                project_url = f"https://141.164.62.222:8080/open/api/json/project/{pcode}/members"
                
                try:
                    response = requests.get(project_url, headers=headers, verify=False)
                    response.raise_for_status()
                    json_resp = response.json()
                    if "data" in json_resp and json_resp["data"] is not None:
                        all_members.extend(json_resp["data"])
                        logging.info(f"Project API returned {len(json_resp['data'])} members")
                    else:
                        logging.warning(f"Project API response missing or null 'data' field: {json_resp}")
                except requests.RequestException as e:
                    logging.warning(f"Project API call failed: {e}")
            else:
                logging.warning("No pcode found in request data for project API call")
        else:
            # groupId가 없는 경우
            # token: ACCOUNT API Key: admin@whatap.io
            pcode = data.get("pcode")
            url = f"https://141.164.62.222:8080/open/api/json/project/{pcode}/members"
            headers = {"x-whatap-token": "ZXFQ1QN2WZKQCXI1B5T6"}
            response = requests.get(url, headers=headers, verify=False)
            response.raise_for_status()
            json_resp = response.json()
            if "data" not in json_resp:
                logging.error(f"API response missing 'data' field: {json_resp}")
                return jsonify({'error': "API response missing 'data' field"}), 500
            if json_resp.get("data") is None:
                logging.error(f"API response 'data' field is None: {json_resp}")
                return jsonify({'error': "API response 'data' field is None"}), 500
            all_members = json_resp.get("data", [])
        
        # 2. 멤버 레벨에서 중복 제거 (이메일 기준)
        unique_members = {}
        for member in all_members:
            email = member.get("email")
            if email:  # 이메일이 있는 경우만 처리
                unique_members[email] = member
        
        logging.info(f"Total members after deduplication: {len(unique_members)}")
        
        # 3. sms 값이 있는 멤버만 추출 (전화번호와 이메일 함께)
        phone_data = []
        for member in unique_members.values():
            if member.get("sms"):
                phone_data.append({
                    "phone": member["sms"],
                    "email": member.get("email", "unknown")
                })
        
        logging.info(f"Total phone numbers found: {len(phone_data)}")
        
        if not phone_data:
            logging.info("No valid phone numbers found in API responses.")
            return jsonify({'status': 'success', 'inserted': 0}), 200
        # 4. 데이터베이스 연결 및 INSERT 처리
        try:
            # 데이터베이스 연결 시도
            conn = oracledb.connect(
              user="",
              password="",
              dsn=oracledb.makedsn("158.247.242.124", 1521, sid="ORA")
            )
            cursor = conn.cursor()
            
            # 현재 최대 TRAN_PR 조회
            today_prefix = datetime.now().strftime('%y%m%d')
            default_tran_pr = int(today_prefix + '0000')
            cursor.execute("SELECT NVL(MAX(TRAN_PR), :default_tran_pr) FROM WHATAP.EM_TRAN2", {'default_tran_pr': default_tran_pr})
            current_max = cursor.fetchone()[0]
            
            # INSERT 쿼리 준비
            sql = """
            INSERT INTO WHATAP.EM_TRAN2 (
                TRAN_PR, TRAN_PHONE, TRAN_CALLBACK, TRAN_STATUS, TRAN_DATE, TRAN_MSG, TRAN_TYPE
            ) VALUES (
                :TRAN_PR, :TRAN_PHONE, :TRAN_CALLBACK, :TRAN_STATUS, SYSDATE, :TRAN_MSG, :TRAN_TYPE
            )
            """
            
            # 각 전화번호에 대해 INSERT 실행
            for i, phone_info in enumerate(phone_data, start=1):
                next_tran_pr = current_max + i
                params = {
                    "TRAN_PR": next_tran_pr,
                    "TRAN_PHONE": phone_info["phone"],
                    "TRAN_CALLBACK": "15882323",
                    "TRAN_STATUS": "1",
                    "TRAN_MSG": data.get("message"),
                    "TRAN_TYPE": 4
                }
                
                # INSERT 쿼리와 파라미터를 결합한 로그 기록
                query_with_values = f"""INSERT INTO WHATAP.EM_TRAN2 (
                TRAN_PR, TRAN_PHONE, TRAN_CALLBACK, TRAN_STATUS, TRAN_DATE, TRAN_MSG, TRAN_TYPE
            ) VALUES (
                {next_tran_pr}, '{phone_info["phone"]}', '15882323', '1', SYSDATE, '{data.get("message", "")}', 4
            )"""
                logging.debug(f"DB INSERT QUERY: {query_with_values.strip()}")
                
                cursor.execute(sql, params)
                logging.info(f"DB INSERT SUCCESS: TRAN_PR={next_tran_pr}, email={phone_info['email']}, TRAN_PHONE={phone_info['phone']}")
            
            conn.commit()
            
            # 처리 완료 마킹
            if request_uuid:
                mark_request_completed(request_uuid)
                
            return jsonify({'status': 'success', 'inserted': len(phone_data)}), 200
            
        except oracledb.DatabaseError as e:
            # 데이터베이스 오류 (연결 오류 포함) 처리
            logging.exception("Database Error:")
            return jsonify({'error': str(e)}), 500
        finally:
            try:
                if 'cursor' in locals() and cursor:
                    cursor.close()
            except Exception as e:
                logging.error(f"cursor.close() failed: {e}")
            try:
                if 'conn' in locals() and conn:
                    conn.close()
            except Exception as e:
                logging.error(f"conn.close() failed: {e}")
                
    except requests.RequestException as e:
        logging.exception("OpenAPI Call Error:")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logging.exception("Unknown Error:")
        return jsonify({'error': str(e)}), 500

def on_exit():
    logging.info("Webhook process has successfully terminated.")

def handle_sigterm(signum, frame):
    logging.info(f"Webhook process is terminated by SIGNAL({signum})")
    sys.exit(0)

atexit.register(on_exit)
signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)

# __main__ 블록은 gunicorn 실행 시 필요 없음. 개발용
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)

# gunicorn -w 4 -b 0.0.0.0:5001 main:app