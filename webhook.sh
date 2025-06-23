#!/bin/bash

# 설정
BIN_PATH=".venv/bin/gunicorn -w 4 -b 0.0.0.0:5001 main:app"
PID_FILE="gunicorn.pid"
VENV_PATH=".venv/bin/activate"
LOG_FILE="logs/event.log"

# 실행 함수
start() {
    if [ -f "$PID_FILE" ]; then
        MSG="Error: gunicorn is already running with PID $(cat $PID_FILE)."
        echo "$MSG"
        echo "$(date '+%Y-%m-%d %H:%M:%S,%3N') INFO $MSG" >> "$LOG_FILE"
    else
        if [ -f "$VENV_PATH" ]; then
            MSG="Activating venv..."
            echo "$MSG"
            echo "$(date '+%Y-%m-%d %H:%M:%S,%3N') INFO $MSG" >> "$LOG_FILE"
            source $VENV_PATH
        else
            MSG="Error: $VENV_PATH not found."
            echo "$MSG"
            echo "$(date '+%Y-%m-%d %H:%M:%S,%3N') ERROR $MSG" >> "$LOG_FILE"
            exit 1
        fi
        MSG="Starting gunicorn..."
        echo "$MSG"
        echo "$(date '+%Y-%m-%d %H:%M:%S,%3N') INFO $MSG" >> "$LOG_FILE"
        nohup $BIN_PATH &> /dev/null &
        echo $! > $PID_FILE
        MSG="gunicorn started with PID $(cat $PID_FILE)."
        echo "$MSG"
        echo "$(date '+%Y-%m-%d %H:%M:%S,%3N') INFO $MSG" >> "$LOG_FILE"
    fi
}

# 상태 함수
status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null; then
            echo "gunicorn is running with PID $PID."
        else
            echo "Error: gunicorn is not running but PID file exists."
            rm -f $PID_FILE
        fi
    else
        echo "gunicorn is not running."
    fi
}

# 중지 함수
stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null; then
            echo "Stopping gunicorn with PID $PID..."
            kill $PID
            rm -f $PID_FILE
            echo "gunicorn stopped."
            if type deactivate 2>/dev/null; then
                deactivate
            fi
        else
            echo "Error: gunicorn is not running."
            rm -f $PID_FILE
        fi
    else
        echo "Error: No PID file found. gunicorn might not be running."
    fi
}

# 매개변수 처리
case "$1" in
    start)
        start
        ;;
    status)
        status
        ;;
    stop)
        stop
        ;;
    *)
        echo "Usage: $0 {start|status|stop}"
        exit 1
        ;;
esac