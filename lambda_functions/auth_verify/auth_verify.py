"""
Lambda function for email verification
Handles verification code confirmation
"""
import json
import boto3
import logging
import os
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Cognito client
cognito = boto3.client('cognito-idp')

# Environment variables
USER_POOL_ID = os.environ.get('USER_POOL_ID')
CLIENT_ID = os.environ.get('CLIENT_ID')

def lambda_handler(event, context):
    """
    Handle email verification requests
    """
    logger.info(f"Verification request received: {json.dumps(event, default=str)}")
    
    # Parse request body
    try:
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Invalid request body'
            })
        }
    
    # Extract parameters
    email = body.get('email')
    code = body.get('code')
    
    # Validate required fields
    if not email or not code:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Email and verification code are required'
            })
        }
    
    try:
        # Confirm the signup
        response = cognito.confirm_sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            ConfirmationCode=code
        )
        
        logger.info(f"User {email} verified successfully")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': 'Email verified successfully. You can now sign in.'
            })
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.error(f"Verification failed: {error_code} - {error_message}")
        
        # Handle specific Cognito errors
        if error_code == 'CodeMismatchException':
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid verification code'
                })
            }
        elif error_code == 'ExpiredCodeException':
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Verification code has expired. Please request a new one.'
                })
            }
        elif error_code == 'NotAuthorizedException':
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'User is already confirmed'
                })
            }
        elif error_code == 'UserNotFoundException':
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'User not found'
                })
            }
        else:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Verification failed. Please try again.'
                })
            }
    
    except Exception as e:
        logger.error(f"Unexpected error during verification: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'An unexpected error occurred'
            })
        }

def resend_verification_code(event, context):
    """
    Resend verification code to user
    """
    logger.info(f"Resend code request received: {json.dumps(event, default=str)}")
    
    # Parse request body
    try:
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Invalid request body'
            })
        }
    
    email = body.get('email')
    
    if not email:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Email is required'
            })
        }
    
    try:
        response = cognito.resend_confirmation_code(
            ClientId=CLIENT_ID,
            Username=email
        )
        
        logger.info(f"Verification code resent to {email}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': 'Verification code sent to your email',
                'codeDeliveryDetails': {
                    'destination': response.get('CodeDeliveryDetails', {}).get('Destination', ''),
                    'deliveryMedium': response.get('CodeDeliveryDetails', {}).get('DeliveryMedium', '')
                }
            })
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.error(f"Resend code failed: {error_code} - {error_message}")
        
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': error_message
            })
        }