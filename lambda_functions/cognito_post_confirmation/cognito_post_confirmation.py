"""
Post-confirmation Lambda trigger for Cognito User Pool
Handles actions after user email verification
"""
import json
import boto3
import logging
from datetime import datetime
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
USER_TABLE_NAME = os.environ.get('USER_PROFILE_TABLE', 'ocr-processor-user-profiles')

def lambda_handler(event, context):
    """
    Post-confirmation trigger
    Creates user profile and initializes user data after email verification
    """
    logger.info(f"Post-confirmation trigger: {json.dumps(event, default=str)}")
    
    try:
        # Extract user information
        user_id = event['request']['userAttributes']['sub']
        email = event['request']['userAttributes']['email']
        name = event['request']['userAttributes'].get('name', '')
        
        # Create user profile in DynamoDB
        table = dynamodb.Table(USER_TABLE_NAME)
        
        user_profile = {
            'user_id': user_id,
            'email': email,
            'name': name,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'email_verified': True,
            'status': 'active',
            'usage_stats': {
                'total_documents': 0,
                'total_pages': 0,
                'storage_used_mb': 0,
                'last_activity': datetime.utcnow().isoformat()
            },
            'preferences': {
                'default_language': 'en',
                'notification_enabled': True,
                'auto_process': True
            },
            'quota': {
                'max_documents_per_month': 1000,
                'max_storage_gb': 10,
                'max_file_size_mb': 100
            }
        }
        
        # Store user profile
        table.put_item(Item=user_profile)
        
        logger.info(f"User profile created for {email} (ID: {user_id})")
        
        # Send welcome email (optional - implement if needed)
        # send_welcome_email(email, name)
        
        # Log successful confirmation
        logger.info(f"Post-confirmation completed for user {email}")
        
        return event
        
    except Exception as e:
        logger.error(f"Post-confirmation processing failed: {str(e)}")
        # Don't raise exception to avoid blocking user confirmation
        # Log error for monitoring
        logger.error(f"Failed to create user profile for {event['request']['userAttributes'].get('email', 'unknown')}: {str(e)}")
        return event

def send_welcome_email(email, name):
    """
    Send welcome email to new user (optional)
    """
    try:
        ses = boto3.client('ses')
        
        # Implement SES email sending if needed
        # ses.send_email(...)
        
        logger.info(f"Welcome email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")