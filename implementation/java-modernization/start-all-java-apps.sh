#!/bin/bash

echo "🚀 Starting All Java Applications (8, 17, 21)"
echo "=============================================="
echo ""

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        echo "⚠️  Port $port is already in use"
        return 1
    else
        echo "✅ Port $port is available"
        return 0
    fi
}

# Function to build and start an application
start_app() {
    local app_name=$1
    local app_dir=$2
    local port=$3
    local java_version=$4
    
    echo ""
    echo "📦 Building $app_name..."
    cd "$app_dir"
    
    if ./mvnw clean package -DskipTests > /dev/null 2>&1; then
        echo "✅ $app_name build successful"
        
        echo "🚀 Starting $app_name on port $port..."
        nohup java -jar target/*.jar > "${app_name}.log" 2>&1 &
        local pid=$!
        echo "📋 $app_name started with PID: $pid"
        
        # Wait a moment for startup
        sleep 3
        
        # Check if process is still running
        if kill -0 $pid 2>/dev/null; then
            echo "✅ $app_name is running successfully on port $port"
            echo "🌐 Access at: http://localhost:$port/"
        else
            echo "❌ $app_name failed to start"
        fi
    else
        echo "❌ $app_name build failed"
    fi
    
    cd - > /dev/null
}

# Check all ports first
echo "🔍 Checking port availability..."
check_port 8080
java8_port_ok=$?
check_port 8081
java17_port_ok=$?
check_port 8082
java21_port_ok=$?

echo ""
echo "🏗️  Building and starting applications..."

# Start Java 8 Application
if [ $java8_port_ok -eq 0 ]; then
    start_app "Java 8 App" "/Users/arptsha/Downloads/repository/ai-powered-modern-application-development/design-and-architecture/java-modernization/java8-app" 8080 "Java 8"
else
    echo "⚠️  Skipping Java 8 app - port 8080 in use"
fi

# Start Java 17 Application
if [ $java17_port_ok -eq 0 ]; then
    start_app "Java 17 App" "/Users/arptsha/Downloads/repository/ai-powered-modern-application-development/design-and-architecture/java-modernization/java17-app" 8081 "Java 17"
else
    echo "⚠️  Skipping Java 17 app - port 8081 in use"
fi

# Start Java 21 Application
if [ $java21_port_ok -eq 0 ]; then
    start_app "Java 21 App" "/Users/arptsha/Downloads/repository/ai-powered-modern-application-development/design-and-architecture/java-modernization/java21-app" 8082 "Java 21"
else
    echo "⚠️  Skipping Java 21 app - port 8082 in use"
fi

echo ""
echo "🎉 Application Startup Summary"
echo "=============================="
echo ""

# Check which applications are running
echo "📊 Running Applications:"
if lsof -i :8080 > /dev/null 2>&1; then
    echo "✅ Java 8 App:  http://localhost:8080/"
else
    echo "❌ Java 8 App:  Not running"
fi

if lsof -i :8081 > /dev/null 2>&1; then
    echo "✅ Java 17 App: http://localhost:8081/"
else
    echo "❌ Java 17 App: Not running"
fi

if lsof -i :8082 > /dev/null 2>&1; then
    echo "✅ Java 21 App: http://localhost:8082/"
else
    echo "❌ Java 21 App: Not running"
fi

echo ""
echo "🎯 Application Features:"
echo "• Java 8:  Traditional patterns, javax.* APIs, legacy features"
echo "• Java 17: Lambda expressions, Stream API, jakarta.* APIs, modern features"
echo "• Java 21: Latest LTS, virtual threads, pattern matching, enhanced features"
echo ""
echo "🔍 To check application logs:"
echo "• Java 8:  tail -f java8-app/Java\\ 8\\ App.log"
echo "• Java 17: tail -f java17-app/Java\\ 17\\ App.log"
echo "• Java 21: tail -f java21-app/Java\\ 21\\ App.log"
echo ""
echo "🛑 To stop all applications:"
echo "   ./stop-all-java-apps.sh"
echo ""
echo "🎉 All applications started! You can now compare Java 8, 17, and 21 features side by side."
