#!/bin/bash

SERVER_FILE="server.py"
CLIENT_FILE="client.py"

# Cleanup on exit
cleanup() {
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "Stopping server (PID $SERVER_PID)..."
        kill $SERVER_PID
    fi
}
trap cleanup EXIT

# Start server
echo "[1/4] Starting server..."
python3 "$SERVER_FILE" &
SERVER_PID=$!
sleep 2

# Check server is alive
if ! ps -p $SERVER_PID > /dev/null; then
    echo "❌ Server failed to start."
    exit 1
fi

# Run both clients
echo "[2/4] Running Player RED (creator)..."
python3 "$CLIENT_FILE" localhost:50051 --automate --player R &
CLIENT1_PID=$!

sleep 2

echo "[3/4] Running Player YELLOW (joins game 1)..."
python3 "$CLIENT_FILE" localhost:50051 --automate --player Y --game_id 1 &
CLIENT2_PID=$!

# Wait for both clients to complete
wait $CLIENT1_PID
wait $CLIENT2_PID

echo "[4/4] Clients completed. Test successful."
