#!/bin/bash
# Start and stop the isolated live simulation. Only recorded processes whose
# command line still matches are stopped. Production servers are never signaled.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIVE_DIR="$ROOT/.live"
URL="http://127.0.0.1:5174/"
API_PORT=5002
WEB_PORT=5174

API_PID="$LIVE_DIR/api.pid"
WEB_PID="$LIVE_DIR/web.pid"
SIM_PID="$LIVE_DIR/simulator.pid"

API_PATTERN='[s]cripts/run_isolated_api.py'
WEB_PATTERN='[v]ite.live.config.ts'
SIM_PATTERN='[s]cripts/live_parking_simulator.py'

mkdir -p "$LIVE_DIR"

command_matches() {
  local pid="$1"
  local pattern="$2"
  local command
  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  [[ -n "$command" ]] || return 1
  printf '%s\n' "$command" | grep -q -- "$pattern"
}

root_pids() {
  local pattern="$1"
  local pid ppid
  local all=""
  all="$(pgrep -f "$pattern" || true)"
  [[ -n "$all" ]] || return 0
  for pid in $all; do
    ppid="$(ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' ' || true)"
    if [[ -z "$ppid" ]] || ! printf '%s\n' "$all" | grep -qx "$ppid"; then
      printf '%s\n' "$pid"
    fi
  done
}

recorded_pid() {
  local pidfile="$1"
  [[ -f "$pidfile" ]] || return 1
  local pid
  pid="$(tr -d '[:space:]' < "$pidfile")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  printf '%s\n' "$pid"
}

terminate() {
  local pid="$1"
  local pattern="$2"
  local child attempt
  kill -TERM "$pid" 2>/dev/null || true
  for child in $(pgrep -P "$pid" || true); do
    if command_matches "$child" "$pattern"; then
      kill -TERM "$child" 2>/dev/null || true
    fi
  done
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.3
  done
  if kill -0 "$pid" 2>/dev/null && command_matches "$pid" "$pattern"; then
    kill -KILL "$pid" 2>/dev/null || true
  fi
}

stop_matching() {
  local name="$1"
  local pidfile="$2"
  local pattern="$3"
  local pid extra stopped=0
  if pid="$(recorded_pid "$pidfile")" && kill -0 "$pid" 2>/dev/null; then
    if command_matches "$pid" "$pattern"; then
      terminate "$pid" "$pattern"
      echo "stopped $name ($pid)"
      stopped=1
    else
      echo "$name pid $pid is no longer the simulation process; it was left running"
    fi
  fi
  rm -f "$pidfile"
  for extra in $(root_pids "$pattern" | sort -u); do
    if command_matches "$extra" "$pattern"; then
      terminate "$extra" "$pattern"
      echo "stopped $name ($extra)"
      stopped=1
    fi
  done
  if [[ "$stopped" -eq 0 ]]; then
    echo "$name is not running"
  fi
}

wait_for_port() {
  local port="$1"
  local attempt
  for attempt in $(seq 1 40); do
    if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  return 1
}

ensure_running() {
  local name="$1"
  local pidfile="$2"
  local pattern="$3"
  local logfile="$4"
  local command="$5"
  local pid roots
  if pid="$(recorded_pid "$pidfile")" && kill -0 "$pid" 2>/dev/null && command_matches "$pid" "$pattern"; then
    echo "$name already running ($pid)"
    return 0
  fi
  rm -f "$pidfile"
  roots="$(root_pids "$pattern" | sort -u)"
  if [[ -n "$roots" ]]; then
    pid="$(printf '%s\n' "$roots" | head -n 1)"
    printf '%s\n' "$pid" > "$pidfile"
    echo "$name already running ($pid)"
    return 0
  fi
  pid="$(python3 - "$logfile" "$command" <<'PY'
import os
import sys

logfile, command = sys.argv[1:]
reader, writer = os.pipe()
if os.fork() > 0:
    os.close(writer)
    sys.stdout.write(os.read(reader, 32).decode())
    raise SystemExit(0)
os.close(reader)
os.setsid()
grandchild = os.fork()
if grandchild > 0:
    os.write(writer, str(grandchild).encode())
    os.close(writer)
    raise SystemExit(0)
os.close(writer)
log = os.open(logfile, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
os.dup2(log, 1)
os.dup2(log, 2)
os.close(log)
devnull = os.open(os.devnull, os.O_RDONLY)
os.dup2(devnull, 0)
os.close(devnull)
os.execv("/bin/bash", ["bash", "-c", command])
PY
)"
  printf '%s\n' "$pid" > "$pidfile"
  sleep 0.2
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "$name failed to start. See $logfile" >&2
    rm -f "$pidfile"
    return 1
  fi
  echo "started $name ($pid)"
}

start_all() {
  ensure_running \
    "isolated API" \
    "$API_PID" \
    "$API_PATTERN" \
    "$LIVE_DIR/api.log" \
    "cd '$ROOT' && exec .venv/bin/python scripts/run_isolated_api.py"
  if ! wait_for_port "$API_PORT"; then
    echo "isolated API did not listen on 127.0.0.1:$API_PORT" >&2
    return 1
  fi

  ensure_running \
    "frontend" \
    "$WEB_PID" \
    "$WEB_PATTERN" \
    "$LIVE_DIR/web.log" \
    "cd '$ROOT/frontend' && exec npm run dev -- --config vite.live.config.ts --host 127.0.0.1 --port $WEB_PORT --strictPort"
  if ! wait_for_port "$WEB_PORT"; then
    echo "frontend did not listen on 127.0.0.1:$WEB_PORT" >&2
    return 1
  fi

  ensure_running \
    "simulator" \
    "$SIM_PID" \
    "$SIM_PATTERN" \
    "$LIVE_DIR/simulator.log" \
    "cd '$ROOT' && exec .venv/bin/python scripts/live_parking_simulator.py"
  echo "Live simulation is running."
  echo "Browser: $URL"
}

stop_simulator() {
  stop_matching "simulator" "$SIM_PID" "$SIM_PATTERN"
  if lsof -nP -iTCP:"$WEB_PORT" -sTCP:LISTEN >/dev/null 2>&1 \
    && lsof -nP -iTCP:"$API_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Simulation stopped. The application is still available."
    echo "Browser: $URL"
  fi
}

shutdown_all() {
  stop_matching "simulator" "$SIM_PID" "$SIM_PATTERN"
  stop_matching "frontend" "$WEB_PID" "$WEB_PATTERN"
  stop_matching "isolated API" "$API_PID" "$API_PATTERN"
}

ensure_application() {
  ensure_running \
    "isolated API" \
    "$API_PID" \
    "$API_PATTERN" \
    "$LIVE_DIR/api.log" \
    "cd '$ROOT' && exec .venv/bin/python scripts/run_isolated_api.py"
  if ! wait_for_port "$API_PORT"; then
    echo "isolated API did not listen on 127.0.0.1:$API_PORT" >&2
    return 1
  fi
  ensure_running \
    "frontend" \
    "$WEB_PID" \
    "$WEB_PATTERN" \
    "$LIVE_DIR/web.log" \
    "cd '$ROOT/frontend' && exec npm run dev -- --config vite.live.config.ts --host 127.0.0.1 --port $WEB_PORT --strictPort"
  if ! wait_for_port "$WEB_PORT"; then
    echo "frontend did not listen on 127.0.0.1:$WEB_PORT" >&2
    return 1
  fi
}

reset_data() {
  stop_matching "simulator" "$SIM_PID" "$SIM_PATTERN"
  "$ROOT/.venv/bin/python" "$ROOT/scripts/reset_simulator_data.py"
  ensure_application
  echo "Simulation remains stopped."
  echo "Browser: $URL"
}

case "${1:-}" in
  start) start_all ;;
  stop) stop_simulator ;;
  shutdown) shutdown_all ;;
  reset) reset_data ;;
  *)
    echo "usage: $0 start|stop|shutdown|reset" >&2
    exit 1
    ;;
esac
