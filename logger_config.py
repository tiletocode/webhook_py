"""
웹훅 서비스를 위한 로깅 설정 모듈
"""
import logging
import os
import glob
from logging.handlers import TimedRotatingFileHandler


class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    """커스텀 로그 파일 핸들러 - 30일 이상 된 로그 파일 자동 삭제"""
    
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

# level, 경로 여기서 수
def setup_logging(log_level=logging.INFO, log_dir='logs', log_file='event.log'):
    """
    로깅 설정을 초기화합니다.
    
    Args:
        log_level: 로그 레벨 (기본값: DEBUG)
        log_dir: 로그 디렉토리 (기본값: 'logs')
        log_file: 로그 파일명 (기본값: 'event.log')
    """
    # 로그 디렉토리 생성
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 로그 파일 경로
    log_file_path = os.path.join(log_dir, log_file)
    
    # 커스텀 핸들러 생성
    handler = CustomTimedRotatingFileHandler(
        log_file_path, 
        when='midnight', 
        interval=1, 
        backupCount=30, 
        encoding='utf-8', 
        utc=False
    )
    handler.suffix = "%y%m%d"
    
    # 포매터 설정
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    
    # 로거 설정
    logger = logging.getLogger()
    logger.handlers = [handler]  # 기존 핸들러 제거하고 새 핸들러 설정
    logger.setLevel(log_level)
    
    return logger


def get_logger():
    """설정된 로거 인스턴스를 반환합니다."""
    return logging.getLogger()
