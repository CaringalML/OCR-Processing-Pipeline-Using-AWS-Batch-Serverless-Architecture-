"""
Lambda function for user registration
Handles signup requests from the frontend
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
    Handle user signup requests
    """
    logger.info(f"Signup request received: {json.dumps(event, default=str)}")
    
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
    
    # Extract signup parameters
    email = body.get('email')
    password = body.get('password')
    name = body.get('name', '')
    organization = body.get('organization', '')
    
    # Validate required fields
    if not email or not password:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Email and password are required'
            })
        }
    
    try:
        # Prepare user attributes
        user_attributes = [
            {'Name': 'email', 'Value': email}
        ]
        
        if name:
            user_attributes.append({'Name': 'name', 'Value': name})
        
        if organization:
            user_attributes.append({'Name': 'custom:organization', 'Value': organization})
        
        # Sign up the user
        response = cognito.sign_up(
            ClientId=CLIENT_ID,
            Username=email,
            Password=password,
            UserAttributes=user_attributes
        )
        
        logger.info(f"User {email} signed up successfully. User Sub: {response['UserSub']}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': 'User registered successfully. Please check your email for verification code.',
                'userSub': response['UserSub'],
                'codeDeliveryDetails': {
                    'destination': response.get('CodeDeliveryDetails', {}).get('Destination', ''),
                    'deliveryMedium': response.get('CodeDeliveryDetails', {}).get('DeliveryMedium', '')
                }
            })
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.error(f"Signup failed: {error_code} - {error_message}")
        
        # Handle specific Cognito errors
        if error_code == 'UsernameExistsException':
            return {
                'statusCode': 409,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'An account with this email already exists'
                })
            }
        elif error_code == 'InvalidPasswordException':
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Password does not meet requirements. Must be at least 8 characters with uppercase, lowercase, numbers, and symbols.'
                })
            }
        elif error_code == 'InvalidParameterException':
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
        else:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Registration failed. Please try again.'
                })
            }
    
    except Exception as e:
        logger.error(f"Unexpected error during signup: {str(e)}")
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