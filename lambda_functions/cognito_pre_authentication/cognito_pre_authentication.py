"""
Pre-authentication Lambda trigger for Cognito User Pool
Validates login attempts and enforces security policies
"""
import json
import boto3
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

# Environment variables
USER_TABLE_NAME = os.environ.get('USER_PROFILE_TABLE', 'ocr-processor-user-profiles')
MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', '5'))
LOCKOUT_DURATION_MINUTES = int(os.environ.get('LOCKOUT_DURATION_MINUTES', '30'))

def lambda_handler(event, context):
    """
    Pre-authentication trigger
    Checks user status and enforces security policies before allowing login
    """
    logger.info(f"Pre-authentication trigger: {json.dumps(event, default=str)}")
    
    try:
        # Extract user information
        # During pre-authentication, 'sub' might not be available, use username instead
        user_id = event['request']['userAttributes'].get('sub') or event['userName']
        email = event['request']['userAttributes'].get('email', event['userName'])
        
        # Get user profile from DynamoDB by email (since sub might not be available yet)
        table = dynamodb.Table(USER_TABLE_NAME)
        
        # Query by email using GSI or scan (assuming email is indexed)
        try:
            # Try to scan for user by email (not ideal but works)
            response = table.scan(
                FilterExpression='email = :email',
                ExpressionAttributeValues={':email': email}
            )
            
            if not response['Items']:
                # User profile doesn't exist - allow login but log warning
                logger.warning(f"User profile not found for {email}")
                return event
            
            user_profile = response['Items'][0]
            # Use the actual user_id from the profile
            actual_user_id = user_profile['user_id']
        except Exception as query_error:
            logger.warning(f"Could not query user profile for {email}: {str(query_error)}")
            # Allow login if we can't check profile
            return event
        
        # Check if user is active
        if user_profile.get('status') != 'active':
            raise Exception(f"Account is {user_profile.get('status', 'inactive')}. Please contact support.")
        
        # Check for account lockout due to failed attempts
        failed_attempts = user_profile.get('failed_login_attempts', 0)
        last_failed_attempt = user_profile.get('last_failed_login')
        
        if failed_attempts >= MAX_LOGIN_ATTEMPTS and last_failed_attempt:
            lockout_time = datetime.fromisoformat(last_failed_attempt) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            if datetime.utcnow() < lockout_time:
                remaining_minutes = int((lockout_time - datetime.utcnow()).total_seconds() / 60)
                raise Exception(f"Account temporarily locked. Try again in {remaining_minutes} minutes.")
            else:
                # Reset failed attempts after lockout period
                table.update_item(
                    Key={'user_id': actual_user_id},
                    UpdateExpression='SET failed_login_attempts = :zero, last_failed_login = :null',
                    ExpressionAttributeValues={
                        ':zero': 0,
                        ':null': None
                    }
                )
        
        # Update last login timestamp
        table.update_item(
            Key={'user_id': actual_user_id},
            UpdateExpression='SET last_login = :now, failed_login_attempts = :zero, #us.last_activity = :now',
            ExpressionAttributeNames={
                '#us': 'usage_stats'
            },
            ExpressionAttributeValues={
                ':now': datetime.utcnow().isoformat(),
                ':zero': 0
            }
        )
        
        logger.info(f"Pre-authentication successful for user {email}")
        
        return event
        
    except Exception as e:
        logger.error(f"Pre-authentication failed: {str(e)}")
        
        # Update failed login attempts
        try:
            if 'actual_user_id' in locals():
                table.update_item(
                    Key={'user_id': actual_user_id},
                    UpdateExpression='SET failed_login_attempts = failed_login_attempts + :one, last_failed_login = :now',
                    ExpressionAttributeValues={
                        ':one': 1,
                        ':now': datetime.utcnow().isoformat()
                    }
                )
        except:
            pass
        
        raise Exception(str(e))