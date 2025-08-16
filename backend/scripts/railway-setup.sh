# Railway Environment Variables Setup Script
# backend/scripts/railway-setup.sh
#!/bin/bash

echo "Setting up Railway environment variables..."

# Set required environment variables
railway variables set SECRET_KEY=$(openssl rand -base64 32)
railway variables set GROQ_API_KEY="$GROQ_API_KEY"
railway variables set QDRANT_URL="$QDRANT_URL" 
railway variables set QDRANT_API_KEY="$QDRANT_API_KEY"
railway variables set ALLOWED_ORIGINS='["https://your-frontend-domain.railway.app"]'

# Optional AWS variables
if [ ! -z "$AWS_ACCESS_KEY_ID" ]; then
    railway variables set AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID"
    railway variables set AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY"
    railway variables set AWS_BUCKET_NAME="$AWS_BUCKET_NAME"
    railway variables set AWS_REGION="us-east-1"
fi

echo "Environment variables set successfully!"
echo "Don't forget to:"
echo "1. Add PostgreSQL service: railway add postgresql"
echo "2. Add Redis service: railway add redis"
echo "3. Update ALLOWED_ORIGINS with your actual frontend URL"
