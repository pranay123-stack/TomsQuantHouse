# Build script for ASYMEdge Dashboard
#!/bin/bash

set -e

echo "🚀 Building ASYMEdge Dashboard..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ and try again."
    exit 1
fi

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
    echo "📦 Installing pnpm..."
    npm install -g pnpm
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/
rm -rf node_modules/.vite-temp/

# Install dependencies
echo "📦 Installing dependencies..."
pnpm install --prefer-offline

# Run linting
echo "🔍 Running linter..."
pnpm lint

# Run type checking
echo "🔍 Running type checking..."
npx tsc --noEmit

# Build for production
echo "🏗 Building for production..."
BUILD_MODE=prod pnpm build

# Analyze bundle size
echo "📊 Analyzing bundle size..."
npx vite-bundle-analyzer dist/stats.html || echo "Bundle analyzer not available"

# Create deployment package
echo "📦 Creating deployment package..."
cd dist
tar -czf ../asymedge-dashboard-v1.0.tar.gz .
cd ..

echo "✅ Build completed successfully!"
echo "📁 Output files:"
echo "   - dist/ (production build)"
echo "   - asymedge-dashboard-v1.0.tar.gz (deployment package)"

# Show build info
echo ""
echo "📋 Build Information:"
echo "   - Node.js: $(node --version)"
echo "   - pnpm: $(pnpm --version)"
echo "   - Build time: $(date)"
echo "   - Environment: production"

# Display file sizes
if [ -d "dist" ]; then
    echo ""
    echo "📊 Bundle Analysis:"
    echo "   - Total files: $(find dist -type f | wc -l)"
    echo "   - Total size: $(du -sh dist | cut -f1)"
    echo "   - JS bundle: $(du -sh dist/assets/*.js 2>/dev/null | head -1 | cut -f1 || echo 'N/A')"
    echo "   - CSS bundle: $(du -sh dist/assets/*.css 2>/dev/null | head -1 | cut -f1 || echo 'N/A')"
fi

echo ""
echo "🎉 ASYMEdge Dashboard build completed successfully!"
echo "Ready for deployment to production environment."