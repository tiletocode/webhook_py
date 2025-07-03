#!/bin/ksh

export TUXDIR=/unify/tuxedo/tuxedo12.2.2.0.0
export TUXRUN=/unify/tuxedo/tuxrun
export TUXCONFIG=$TUXRUN/apps/protosys/tuxconfig
export LIBPATH=$LIBPATH:$TUXDIR/lib
export PATH=$TUXDIR/bin:$PATH

if [ $# -ne 1 ]; then
    echo "-1 chkq-err tx q-name q-time"
    exit 1
fi

IN_ARG=$1

DATE=$(date +"%Y%m%d")
LOGFILE=${LOGHOME}/flog/qlog/chkq.${DATE}.${HOSTNAME}.txt

if [ -f "$LOGFILE" ]; then
    >> "$LOGFILE"
else
    > "$LOGFILE"
fi

qtime=$(date +"%Y%m%d%H%M%S")

echo pq | tmadmin -r 2>/dev/null | grep -e "$IN_ARG" | \
    awk -v qtime="$qtime" '
        {
            if ( $5 >= 0 && substr($1, 3, 2) == "me" ) {
                printf "{\"progName\":\"%s\", ", $1;
                printf "\"QueueName\":\"%s\", ", $2;
                printf "\"Serve\":%s, ", $3;
                printf "\"WK Queued\":%s, ", $4;
                printf "\"Queued\":%s, ", $5;
                printf "\"Ave. Len\":%s, ", $6;
                printf "\"Machine\":\"%s\", ", $7;
                printf "\"qtime\":\"%s\"}", qtime;
                printf "\n";
            }
        }' | tee -a "$LOGFILE"
