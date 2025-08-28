"""
Common authentication utilities for Lambda functions
Provides user context extraction and validation
"""
import json
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def extract_user_context(event: Dict) -> Dict:
    """
    Extract user context from API Gateway event with Cognito authorizer
    
    Args:
        event: Lambda event from API Gateway
        
    Returns:
        Dictionary with user information
        
    Raises:
        Exception: If user context is missing or invalid
    """
    try:
        # Check if authorizer context exists
        if 'requestContext' not in event:
            raise Exception("Missing request context")
        
        request_context = event['requestContext']
        
        # Extract from Cognito authorizer
        if 'authorizer' in request_context and 'claims' in request_context['authorizer']:
            claims = request_context['authorizer']['claims']
            
            user_context = {
                'user_id': claims.get('sub'),
                'email': claims.get('email'),
                'email_verified': claims.get('email_verified') == 'true',
                'name': claims.get('name', ''),
                'organization': claims.get('custom:organization', ''),
                'cognito_username': claims.get('cognito:username', claims.get('email'))
            }
            
            # Validate required fields
            if not user_context['user_id']:
                raise Exception("User ID not found in token")
            
            if not user_context['email']:
                raise Exception("Email not found in token")
            
            logger.info(f"User context extracted for {user_context['email']} (ID: {user_context['user_id']})")
            return user_context
            
        # Fallback to checking Authorization header directly (for testing)
        elif 'headers' in event and 'Authorization' in event['headers']:
            # This would require JWT decoding - implement if needed
            raise Exception("Direct JWT decoding not implemented. Use API Gateway Cognito authorizer.")
        else:
            raise Exception("No authorization information found")
            
    except Exception as e:
        logger.error(f"Failed to extract user context: {str(e)}")
        raise Exception(f"Unauthorized: {str(e)}")

def create_user_scoped_id(user_id: str, resource_id: str) -> str:
    """
    Create a user-scoped composite ID for DynamoDB
    
    Args:
        user_id: Cognito user ID (sub)
        resource_id: Resource identifier (file_id, etc.)
        
    Returns:
        Composite ID in format: user_id#resource_id
    """
    return f"{user_id}#{resource_id}"

def parse_user_scoped_id(composite_id: str) -> Tuple[str, str]:
    """
    Parse a user-scoped composite ID
    
    Args:
        composite_id: Composite ID in format user_id#resource_id
        
    Returns:
        Tuple of (user_id, resource_id)
    """
    parts = composite_id.split('#', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid composite ID format: {composite_id}")
    return parts[0], parts[1]

def is_user_authorized(user_id: str, resource_user_id: str) -> bool:
    """
    Check if user is authorized to access a resource
    
    Args:
        user_id: Current user's ID
        resource_user_id: User ID associated with the resource
        
    Returns:
        True if authorized, False otherwise
    """
    return user_id == resource_user_id

def filter_user_items(items: list, user_id: str, id_field: str = 'file_id') -> list:
    """
    Filter items to only include those belonging to the user
    
    Args:
        items: List of items from DynamoDB
        user_id: Current user's ID
        id_field: Field name containing the composite ID
        
    Returns:
        Filtered list of items
    """
    filtered_items = []
    
    for item in items:
        if id_field in item:
            try:
                item_user_id, _ = parse_user_scoped_id(item[id_field])
                if item_user_id == user_id:
                    filtered_items.append(item)
            except:
                # Skip items with invalid ID format
                continue
        elif 'user_id' in item and item['user_id'] == user_id:
            # Direct user_id field
            filtered_items.append(item)
    
    return filtered_items

def add_user_context_to_item(item: Dict, user_context: Dict) -> Dict:
    """
    Add user context fields to a DynamoDB item
    
    Args:
        item: Item to be stored in DynamoDB
        user_context: User context from extract_user_context
        
    Returns:
        Item with added user context fields
    """
    item['user_id'] = user_context['user_id']
    item['user_email'] = user_context['email']
    
    if user_context.get('organization'):
        item['user_organization'] = user_context['organization']
    
    return item

def create_unauthorized_response(message: str = "Unauthorized") -> Dict:
    """
    Create a standardized unauthorized response
    
    Args:
        message: Error message
        
    Returns:
        API Gateway response dictionary
    """
    return {
        'statusCode': 401,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': message
        })
    }

def create_forbidden_response(message: str = "Access forbidden") -> Dict:
    """
    Create a standardized forbidden response
    
    Args:
        message: Error message
        
    Returns:
        API Gateway response dictionary
    """
    return {
        'statusCode': 403,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'error': message
        })
    }