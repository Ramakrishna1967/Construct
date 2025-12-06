# Deployment script for Render.com (Windows)

Write-Host "🚀 Deploying to Render.com..." -ForegroundColor Green

# Check if git repo exists
if (-Not (Test-Path .git)) {
    Write-Host "📦 Initializing git repository..." -ForegroundColor Yellow
    git init
    git add .
    git commit -m "Initial commit for Render deployment"
}

Write-Host "✅ Repository ready!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Push to GitHub:"
Write-Host "   git remote add origin <your-github-repo-url>"
Write-Host "   git push -u origin main"
Write-Host ""
Write-Host "2. Go to https://render.com and sign up (free, no credit card)" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Click 'New +' → 'Blueprint'"
Write-Host ""
Write-Host "4. Connect your GitHub repository"
Write-Host ""
Write-Host "5. Render will automatically detect render.yaml"
Write-Host ""
Write-Host "6. In the Render dashboard, add your GOOGLE_API_KEY:"
Write-Host "   - Go to your service → Environment"
Write-Host "   - Add: GOOGLE_API_KEY=your_actual_key_here" -ForegroundColor Yellow
Write-Host ""
Write-Host "7. Click 'Apply' to deploy!"
Write-Host ""
Write-Host "🎉 Your app will be live at: https://ai-code-reviewer.onrender.com" -ForegroundColor Green
