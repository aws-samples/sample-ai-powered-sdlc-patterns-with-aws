#!/bin/bash

echo "🧹 Cleaning up Java Modernization project for git checkin..."

# Remove .DS_Store files (Mac specific)
echo "Removing .DS_Store files..."
find . -name ".DS_Store" -type f -delete

# Remove log files
echo "Removing log files..."
find . -name "*.log" -type f -delete
find . -name "*.log.*" -type f -delete
find . -name "*.gz" -type f -delete

# Remove Maven target directories
echo "Removing Maven target directories..."
find . -name "target" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove compiled JAR files
echo "Removing JAR files..."
find . -name "*.jar" -type f -delete

# Remove the large zip file
echo "Removing zip files..."
find . -name "*.zip" -type f -delete

# Remove VS Code settings
echo "Removing VS Code settings..."
rm -rf .vscode/

# Remove any temporary files
echo "Removing temporary files..."
find . -name "*.tmp" -type f -delete
find . -name "*.temp" -type f -delete
find . -name "*~" -type f -delete

# Remove any backup files
echo "Removing backup files..."
find . -name "*.orig" -type f -delete
find . -name "*.bak" -type f -delete

# Clean up any empty directories (except .git)
echo "Removing empty directories..."
find . -type d -empty -not -path "./.git*" -delete 2>/dev/null || true

echo "✅ Cleanup completed!"
echo ""
echo "📊 Current directory size:"
du -sh .
echo ""
echo "📁 Files remaining:"
find . -type f -not -path "./.git/*" | wc -l | xargs echo "Total files:"
echo ""
echo "🚀 Project is now ready for git checkin!"
