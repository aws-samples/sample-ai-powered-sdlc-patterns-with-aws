#!/bin/bash

echo "🛑 Stopping All Java Applications"
echo "================================="
echo ""

# Function to stop application on a specific port
stop_app_on_port() {
    local port=$1
    local app_name=$2
    
    echo "🔍 Checking for $app_name on port $port..."
    
    # Find process using the port
    local pid=$(lsof -ti :$port)
    
    if [ -n "$pid" ]; then
        echo "🛑 Stopping $app_name (PID: $pid)..."
        kill -15 $pid
        
        # Wait for graceful shutdown
        sleep 3
        
        # Check if still running, force kill if necessary
        if kill -0 $pid 2>/dev/null; then
            echo "⚠️  Force killing $app_name..."
            kill -9 $pid
        fi
        
        echo "✅ $app_name stopped"
    else
        echo "ℹ️  $app_name not running on port $port"
    fi
}

# Stop all applications
stop_app_on_port 8080 "Java 8 App"
stop_app_on_port 8081 "Java 17 App"
stop_app_on_port 8082 "Java 21 App"

echo ""
echo "🧹 Cleaning up log files..."
rm -f /Users/arptsha/Downloads/modernization/java8-app/Java\ 8\ App.log
rm -f /Users/arptsha/Downloads/modernization/java17-app/Java\ 17\ App.log
rm -f /Users/arptsha/Downloads/modernization/java21-app/Java\ 21\ App.log

echo ""
echo "✅ All Java applications stopped and cleaned up!"
echo ""
echo "📊 Port Status:"
if lsof -i :8080 > /dev/null 2>&1; then
    echo "⚠️  Port 8080: Still in use"
else
    echo "✅ Port 8080: Available"
fi

if lsof -i :8081 > /dev/null 2>&1; then
    echo "⚠️  Port 8081: Still in use"
else
    echo "✅ Port 8081: Available"
fi

if lsof -i :8082 > /dev/null 2>&1; then
    echo "⚠️  Port 8082: Still in use"
else
    echo "✅ Port 8082: Available"
fi

echo ""
echo "🎉 Ready to start applications again with ./start-all-java-apps.sh"
