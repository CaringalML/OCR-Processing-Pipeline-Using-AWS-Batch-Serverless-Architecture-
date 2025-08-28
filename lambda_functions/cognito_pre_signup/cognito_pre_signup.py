"""
Pre-signup Lambda trigger for Cognito User Pool
Validates user registration data before account creation
"""
import json
import re
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def validate_email(email):
    """Validate email format"""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def lambda_handler(event, context):
    """
    Pre-signup trigger
    Validates user data before allowing registration
    """
    logger.info(f"Pre-signup trigger: {json.dumps(event, default=str)}")
    
    try:
        # Extract user attributes
        email = event['request']['userAttributes'].get('email', '')
        name = event['request']['userAttributes'].get('name', '')
        
        # Validate email format
        if not validate_email(email):
            raise Exception("Invalid email format")
        
        # Check for blocked domains (optional - add your logic here)
        blocked_domains = ['tempmail.com', 'throwaway.email', 'guerrillamail.com']
        email_domain = email.split('@')[1].lower()
        if email_domain in blocked_domains:
            raise Exception("Email domain not allowed. Please use a valid email address.")
        
        # Auto-confirm user if email matches admin pattern (optional)
        admin_domains = ['admin.com']  # Replace with your admin domains
        if email_domain in admin_domains:
            event['response']['autoConfirmUser'] = True
            event['response']['autoVerifyEmail'] = True
        else:
            # Regular users need to verify their email
            event['response']['autoConfirmUser'] = False
            event['response']['autoVerifyEmail'] = False
        
        # Add any custom validation here
        # For example, check if organization is required
        organization = event['request']['userAttributes'].get('custom:organization', '')
        
        # Log successful validation
        logger.info(f"User {email} passed pre-signup validation")
        
        return event
        
    except Exception as e:
        logger.error(f"Pre-signup validation failed: {str(e)}")
        raise Exception(f"Registration failed: {str(e)}")