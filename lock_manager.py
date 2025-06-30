"""
웹훅 요청 중복 처리 방지를 위한 파일 기반 락 매니저
"""
import os
import time
import logging


def get_lock_dir():
    """프로젝트 루트의 .lock 디렉토리 경로 반환"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    lock_dir = os.path.join(script_dir, '.lock')
    if not os.path.exists(lock_dir):
        try:
            os.makedirs(lock_dir, exist_ok=True)
        except Exception as e:
            logging.debug(f"Failed to create lock directory: {e}")
    return lock_dir


def is_request_processed(uuid):
    """파일 기반으로 요청 처리 여부 확인 및 마킹 (2단계 락)"""
    lock_dir = get_lock_dir()
    processing_file = os.path.join(lock_dir, f"webhook_{uuid}.processing")
    completed_file = os.path.join(lock_dir, f"webhook_{uuid}.completed")
    
    try:
        # 1단계: 완료된 요청 체크
        if os.path.exists(completed_file):
            try:
                stat = os.stat(completed_file)
                if time.time() - stat.st_mtime < 300:  # 5분
                    return True  # 이미 완료된 요청
                else:
                    # 만료된 완료 파일 삭제
                    try:
                        os.remove(completed_file)
                    except:
                        pass
            except:
                pass
        
        # 2단계: 처리 중인 요청 체크 및 마킹
        if os.path.exists(processing_file):
            try:
                stat = os.stat(processing_file)
                if time.time() - stat.st_mtime < 60:  # 1분 (처리 중)
                    return True  # 다른 워커가 처리 중
                else:
                    # 1분 초과 시 처리 실패로 간주하고 삭제
                    try:
                        os.remove(processing_file)
                    except:
                        pass
            except:
                pass
        
        # 3단계: 처리 시작 마킹
        try:
            with open(processing_file, 'x') as f:
                f.write(str(time.time()))
            return False  # 처리 시작
        except FileExistsError:
            return True  # 다른 워커가 이미 시작
            
    except Exception as e:
        logging.debug(f"UUID check failed for {uuid}: {e}")
        return False  # 안전한 쪽으로 처리 허용


def mark_request_completed(uuid):
    """요청 처리 완료 마킹"""
    lock_dir = get_lock_dir()
    processing_file = os.path.join(lock_dir, f"webhook_{uuid}.processing")
    completed_file = os.path.join(lock_dir, f"webhook_{uuid}.completed")
    
    try:
        # 완료 파일 생성
        with open(completed_file, 'w') as f:
            f.write(str(time.time()))
        
        # 처리 중 파일 삭제
        try:
            os.remove(processing_file)
        except:
            pass
    except Exception as e:
        logging.debug(f"Failed to mark request completed for {uuid}: {e}")


def cleanup_old_lock_files(max_age_hours=24):
    """오래된 락 파일들을 정리하는 유틸리티 함수"""
    lock_dir = get_lock_dir()
    if not os.path.exists(lock_dir):
        return
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    try:
        for filename in os.listdir(lock_dir):
            if filename.startswith('webhook_') and (filename.endswith('.processing') or filename.endswith('.completed')):
                file_path = os.path.join(lock_dir, filename)
                try:
                    stat = os.stat(file_path)
                    if current_time - stat.st_mtime > max_age_seconds:
                        os.remove(file_path)
                        logging.debug(f"Cleaned up old lock file: {filename}")
                except Exception as e:
                    logging.debug(f"Failed to cleanup lock file {filename}: {e}")
    except Exception as e:
        logging.debug(f"Failed to cleanup lock directory: {e}")
