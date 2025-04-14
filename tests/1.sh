#!/bin/bash

# File names
PROTO_FILE="game.proto"
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

# Step 1: Compile proto
echo "[1/5] Compiling $PROTO_FILE..."
python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. "$PROTO_FILE" || {
    echo "❌ Failed to compile proto file."
    exit 1
}

# Step 2: Start the server in background
echo "[2/5] Starting server in background..."
python3 "$SERVER_FILE" &
SERVER_PID=$!
sleep 2

# Step 3: Check server status
if ! ps -p $SERVER_PID > /dev/null; then
    echo "❌ Server failed to start or crashed."
    exit 1
fi
echo "✅ Server is running (PID: $SERVER_PID)"

# Step 4: Run Player RED (create game)
echo "[3/5] Launching Player RED (creates game)..."
python3 "$CLIENT_FILE" localhost:50051 --automate --player R &
CLIENT1_PID=$!

sleep 2

# Step 5: Run Player YELLOW (joins game with game ID 1)
echo "[4/5] Launching Player YELLOW (joins game 1)..."
python3 "$CLIENT_FILE" localhost:50051 --automate --player Y --game_id 1 &
CLIENT2_PID=$!

# Wait for both clients to finish
wait $CLIENT1_PID
wait $CLIENT2_PID

# Step 6: Shutdown server
echo "[5/5] All clients finished. Shutting down server..."
kill $SERVER_PID
