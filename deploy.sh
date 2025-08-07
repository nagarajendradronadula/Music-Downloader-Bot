#!/bin/bash

# AWS Lambda Deployment Script
echo "🚀 Deploying Music Bot to AWS Lambda..."

# Create deployment package
mkdir -p lambda-package
cp lambda_bot.py lambda-package/
cp requirements_aws.txt lambda-package/requirements.txt

# Install dependencies
cd lambda-package
pip install -r requirements.txt -t .

# Create ZIP file
zip -r ../music-bot-lambda.zip .
cd ..

# Deploy to AWS Lambda (you'll need AWS CLI configured)
echo "📦 Package created: music-bot-lambda.zip"
echo "🔧 Next steps:"
echo "1. Upload music-bot-lambda.zip to AWS Lambda"
echo "2. Set environment variable BOT_TOKEN"
echo "3. Set up API Gateway webhook"
echo "4. Configure S3 bucket for file storage"

# Cleanup
rm -rf lambda-package

echo "✅ Deployment package ready!"