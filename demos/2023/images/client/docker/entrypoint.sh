#!/bin/sh

w_output=$HOME/.output
w_pidfile=$HOME/.local/cryton-worker/worker.pid
w_exec=$HOME/.local/cryton-worker/venv/bin/cryton-worker
p_exec=$HOME/.local/cryton-worker/venv/bin/python

start-stop-daemon --start --quiet --background --output $w_output --pidfile $w_pidfile --exec $p_exec -- $w_exec start --persistent

w2_output=/human-agent/.output
w2_pidfile=/human-agent/.human.pid
p2_exec=/human-agent/venv/bin/python

start-stop-daemon --start --quiet --background --output $w2_output --pidfile $w2_pidfile --exec $p2_exec -- -m uvicorn humanbot_agent.app:app --host 127.0.0.1 --port 8042

exec "$@"
