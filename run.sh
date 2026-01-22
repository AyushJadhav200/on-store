#!/bin/bash
# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Installing dependencies..."
    ./venv/bin/pip install -r requirements.txt
fi

echo "Starting Swara's Fashion Server..."
echo "Opening http://127.0.0.1:5000 in your browser..."

# Kill any existing process on port 5000 (prevents 'Address already in use')
fuser -k 5000/tcp > /dev/null 2>&1

# Start server in background
./venv/bin/python app.py &

# Wait a moment for server to start then open browser
sleep 2
xdg-open http://127.0.0.1:5000

# Keep script running to keep server alive
wait
