#!/bin/bash

# 설정
BIN_PATH="gunicorn -w 4 -b 0.0.0.0:5001 main:app"
PID_FILE="gunicorn.pid"
VENV_PATH=".venv/bin/activate"

# 실행 함수
start() {
    if [ -f "$PID_FILE" ]; then
        echo "Error: gunicorn is already running with PID $(cat $PID_FILE)."
    else
        if [ -f "$VENV_PATH" ]; then
            echo "Activating venv..."
            source $VENV_PATH
        else
            echo "Error: $VENV_PATH not found."
            exit 1
        fi
        echo "Starting gunicorn..."
        nohup $BIN_PATH &> /dev/null &
        echo $! > $PID_FILE
        echo "gunicorn started with PID $(cat $PID_FILE)."
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