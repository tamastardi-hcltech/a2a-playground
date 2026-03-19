#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${LOG_DIR}"

pids=()
names=()
reported_dead=()

kill_tree_term() {
  local pid="$1"
  local children
  children="$(pgrep -P "${pid}" 2>/dev/null || true)"
  for child in ${children}; do
    kill_tree_term "${child}"
  done
  kill -TERM "${pid}" 2>/dev/null || true
}

kill_tree_kill() {
  local pid="$1"
  local children
  children="$(pgrep -P "${pid}" 2>/dev/null || true)"
  for child in ${children}; do
    kill_tree_kill "${child}"
  done
  kill -KILL "${pid}" 2>/dev/null || true
}

cleanup() {
  echo
  echo "Stopping services..."
  for pid in "${pids[@]:-}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill_tree_term "${pid}"
    fi
  done
  sleep 1
  for pid in "${pids[@]:-}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill_tree_kill "${pid}"
    fi
  done
  wait || true
}

trap cleanup EXIT INT TERM

check_port_free() {
  local name="$1"
  local port="$2"
  if lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port ${port} already in use (${name})."
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN || true
    echo "Stop the existing process, then re-run ./scripts/start_all.sh"
    exit 1
  fi
}

start_service() {
  local name="$1"
  local port="$2"
  local cmd="$3"
  local log_file="${LOG_DIR}/${name}.log"

  echo "Starting ${name} on port ${port}..."
  bash -lc "cd \"${ROOT_DIR}\" && exec ${cmd}" >"${log_file}" 2>&1 &
  local pid=$!
  pids+=("${pid}")
  names+=("${name}")
  reported_dead+=("0")
  echo "  pid=${pid} log=${log_file}"
}

check_port_free "web_search_agent" 8000
check_port_free "astrology_agent" 8001
check_port_free "tarot_agent" 8002
check_port_free "orchestrator_agent" 8010

start_service "web_search_agent" 8000 "uv run --env-file web_search_agent/.env python -m web_search_agent.main"
start_service "astrology_agent" 8001 "uv run --env-file astrology_agent/.env python -m astrology_agent.main"
start_service "tarot_agent" 8002 "uv run --env-file tarot_agent/.env python -m tarot_agent.main"
start_service "orchestrator_agent" 8010 "uv run --env-file orchestrator_agent/.env python -m orchestrator_agent.main"

echo
echo "All services started."
echo "Press Ctrl+C to stop all."
echo "Tail logs with: tail -f logs/orchestrator_agent.log"

while true; do
  alive_count=0
  for i in "${!pids[@]}"; do
    pid="${pids[$i]}"
    name="${names[$i]}"
    if kill -0 "${pid}" 2>/dev/null; then
      alive_count=$((alive_count + 1))
    else
      if [[ "${reported_dead[$i]}" == "0" ]]; then
        echo "Service exited: ${name} (pid=${pid}). Check logs/${name}.log"
        reported_dead[$i]="1"
      fi
    fi
  done

  if [[ "${alive_count}" -eq 0 ]]; then
    echo "All services have exited."
    break
  fi

  sleep 1
done
