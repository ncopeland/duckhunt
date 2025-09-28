#!/bin/bash

# DuckHunt Bot Wrapper Script
# Automatically restarts the bot when it exits

BOT_SCRIPT="duckhunt_bot.py"
LOG_FILE="duckhunt.log"
PID_FILE="duckhunt.pid"
MAX_LOG_BYTES=$((10*1024*1024))

trim_log() {
  if [ -f "$LOG_FILE" ]; then
    size=$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$size" -gt "$MAX_LOG_BYTES" ]; then
      # Keep the last N bytes within limit by trimming oldest lines
      # Approximate by keeping last 9.5MB to reduce churn
      keep=$((MAX_LOG_BYTES - 524288))
      tail -c "$keep" "$LOG_FILE" > "$LOG_FILE.tmp" 2>/dev/null || true
      mv "$LOG_FILE.tmp" "$LOG_FILE" 2>/dev/null || true
    fi
  fi
}

# Function to start the bot
start_bot() {
  echo "$(date): Starting DuckHunt Bot..." | tee -a "$LOG_FILE"
  trim_log
  python3 "$BOT_SCRIPT" >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  echo "$(date): Bot started with PID $(cat $PID_FILE)" | tee -a "$LOG_FILE"
  trim_log
}

# Function to stop the bot
stop_bot() {
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
      echo "$(date): Stopping bot (PID: $PID)..." | tee -a "$LOG_FILE"
      kill "$PID"
      rm -f "$PID_FILE"
    else
      echo "$(date): Bot process not running" | tee -a "$LOG_FILE"
      rm -f "$PID_FILE"
    fi
  else
    echo "$(date): No PID file found" | tee -a "$LOG_FILE"
  fi
  trim_log
}

# Function to check if bot is running
is_running() {
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
      return 0
    else
      rm -f "$PID_FILE"
      return 1
    fi
  else
    return 1
  fi
}

# Handle signals
cleanup() {
  echo "$(date): Received signal, stopping bot..." | tee -a "$LOG_FILE"
  stop_bot
  exit 0
}

trap cleanup SIGTERM SIGINT

# Main loop
echo "$(date): DuckHunt Bot Wrapper started" | tee -a "$LOG_FILE"
trim_log

while true; do
  if ! is_running; then
    start_bot
  fi
  
  # Wait for bot to exit
  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    while kill -0 "$PID" 2>/dev/null; do
      sleep 1
    done
    echo "$(date): Bot exited, restarting in 5 seconds..." | tee -a "$LOG_FILE"
    trim_log
    sleep 5
  else
    sleep 1
  fi
done

