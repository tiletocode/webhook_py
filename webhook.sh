#!/bin/bash

# 설정
BIN_PATH="python main.py"
PID_FILE="main.pid"

# 실행 함수
start() {
    if [ -f "$PID_FILE" ]; then
        echo "Error: main.bin is already running with PID $(cat $PID_FILE)."
    else
        echo "Starting main.bin..."
        nohup $BIN_PATH &> /dev/null &
        echo $! > $PID_FILE
        echo "main.bin started with PID $(cat $PID_FILE)."
    fi
}

# 상태 함수
status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null; then
            echo "main.bin is running with PID $PID."
        else
            echo "Error: main.bin is not running but PID file exists."
            rm -f $PID_FILE
        fi
    else
        echo "main.bin is not running."
    fi
}

# 중지 함수
stop() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null; then
            echo "Stopping main.bin with PID $PID..."
            kill $PID
            rm -f $PID_FILE
            echo "main.bin stopped."
        else
            echo "Error: main.bin is not running."
            rm -f $PID_FILE
        fi
    else
        echo "Error: No PID file found. main.bin might not be running."
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