#!/bin/bash
# Deployment script for Render.com

echo "🚀 Deploying to Render.com..."

# Check if git repo exists
if [ ! -d .git ]; then
    echo "📦 Initializing git repository..."
    git init
    git add .
    git commit -m "Initial commit for Render deployment"
fi

echo "✅ Repository ready!"
echo ""
echo "📋 Next steps:"
echo "1. Push to GitHub:"
echo "   git remote add origin <your-github-repo-url>"
echo "   git push -u origin main"
echo ""
echo "2. Go to https://render.com and sign up (free, no credit card)"
echo ""
echo "3. Click 'New +' → 'Blueprint'"
echo ""
echo "4. Connect your GitHub repository"
echo ""
echo "5. Render will automatically detect render.yaml"
echo ""
echo "6. In the Render dashboard, add your GOOGLE_API_KEY:"
echo "   - Go to your service → Environment"
echo "   - Add: GOOGLE_API_KEY=your_actual_key_here"
echo ""
echo "7. Click 'Apply' to deploy!"
echo ""
echo "🎉 Your app will be live at: https://ai-code-reviewer.onrender.com"
