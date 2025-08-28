"""
Lambda function for user sign-in
Handles authentication requests from the frontend
"""
import json
import boto3
import logging
import os
import hashlib
import hmac
import base64
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Cognito client
cognito = boto3.client('cognito-idp')

# Environment variables
USER_POOL_ID = os.environ.get('USER_POOL_ID')
CLIENT_ID = os.environ.get('CLIENT_ID')

def get_secret_hash(username, client_id, client_secret=None):
    """
    Calculate secret hash for Cognito if client secret exists
    """
    if not client_secret:
        return None
    
    message = bytes(username + client_id, 'utf-8')
    key = bytes(client_secret, 'utf-8')
    secret_hash = base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
    
    return secret_hash

def lambda_handler(event, context):
    """
    Handle user sign-in requests
    """
    logger.info(f"Sign-in request received: {json.dumps(event, default=str)}")
    
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
    password = body.get('password')
    
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
        # Initiate auth
        auth_params = {
            'USERNAME': email,
            'PASSWORD': password
        }
        
        response = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters=auth_params
        )
        
        # Check if MFA is required
        if 'ChallengeName' in response:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': False,
                    'challengeName': response['ChallengeName'],
                    'session': response.get('Session', ''),
                    'challengeParameters': response.get('ChallengeParameters', {})
                })
            }
        
        # Extract tokens
        auth_result = response.get('AuthenticationResult', {})
        
        # Get user info
        user_response = cognito.get_user(
            AccessToken=auth_result['AccessToken']
        )
        
        # Extract user attributes
        user_attributes = {}
        for attr in user_response.get('UserAttributes', []):
            user_attributes[attr['Name']] = attr['Value']
        
        logger.info(f"User {email} signed in successfully")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'message': 'Sign-in successful',
                'tokens': {
                    'accessToken': auth_result['AccessToken'],
                    'idToken': auth_result['IdToken'],
                    'refreshToken': auth_result['RefreshToken'],
                    'expiresIn': auth_result['ExpiresIn']
                },
                'user': {
                    'userId': user_attributes.get('sub'),
                    'email': user_attributes.get('email'),
                    'emailVerified': user_attributes.get('email_verified') == 'true',
                    'name': user_attributes.get('name', ''),
                    'organization': user_attributes.get('custom:organization', '')
                }
            })
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        logger.error(f"Sign-in failed: {error_code} - {error_message}")
        
        # Handle specific Cognito errors
        if error_code == 'NotAuthorizedException':
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid email or password'
                })
            }
        elif error_code == 'UserNotConfirmedException':
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Email not verified. Please verify your email first.',
                    'requiresVerification': True
                })
            }
        elif error_code == 'UserNotFoundException':
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Invalid email or password'
                })
            }
        elif error_code == 'PasswordResetRequiredException':
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Password reset required',
                    'requiresPasswordReset': True
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
                    'error': 'Sign-in failed. Please try again.'
                })
            }
    
    except Exception as e:
        logger.error(f"Unexpected error during sign-in: {str(e)}")
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

def refresh_token_handler(event, context):
    """
    Refresh access token using refresh token
    """
    logger.info("Token refresh request received")
    
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
    
    refresh_token = body.get('refreshToken')
    
    if not refresh_token:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Refresh token is required'
            })
        }
    
    try:
        response = cognito.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={
                'REFRESH_TOKEN': refresh_token
            }
        )
        
        auth_result = response.get('AuthenticationResult', {})
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'tokens': {
                    'accessToken': auth_result['AccessToken'],
                    'idToken': auth_result['IdToken'],
                    'expiresIn': auth_result['ExpiresIn']
                }
            })
        }
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.error(f"Token refresh failed: {error_code}")
        
        return {
            'statusCode': 401,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Invalid refresh token'
            })
        }