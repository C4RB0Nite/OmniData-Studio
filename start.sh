#!/bin/bash

# Function to handle shutdown
cleanup() {
    echo ""
    echo "Shutting down OmniData Studio..."
    # Kill the background processes
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    echo "All servers terminated."
    exit
}

# Trap Ctrl+C (Interrupt signal) to run the cleanup function
trap cleanup SIGINT

echo "==================================================="
echo "       OmniData Studio - Master Launcher"
echo "==================================================="
echo ""

# 1. Verify Python Dependencies
# (pip automatically skips packages already installed)
echo "[1/2] Verifying Python Dependencies..."
pip3 install -r requirements.txt
echo ""

# 2. Verify UI Dependencies
# (npm automatically skips packages already installed)
echo "[2/2] Verifying UI Dependencies..."
cd data-os-frontend
npm install
cd ..
echo ""

# 3. Boot the Servers
echo "==================================================="
echo "Booting Cognitive Architecture..."
echo "==================================================="

# Launch Backend in background
python3 server.py &
BACKEND_PID=$!

# Launch Frontend in background
cd data-os-frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "[SUCCESS] Both servers are running in the background."
echo "The UI is available at: http://localhost:3000"
echo ""
echo "==================================================="
echo "               🛑 SHUTDOWN SEQUENCE 🛑"
echo "==================================================="
echo "To shut down both servers, simply press CTRL+C"
echo "in this terminal window."
echo "==================================================="

# Keep the script alive so the trap can catch the signal
wait