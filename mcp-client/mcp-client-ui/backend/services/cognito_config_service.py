"""
AWS Cognito Configuration Service

This service manages AWS Cognito User Pool configuration, group management,
and IAM role setup for the iCode authentication system.
"""

import boto3
import logging
from typing import Dict, List, Optional, Any
from botocore.exceptions import ClientError, NoCredentialsError
from dataclasses import dataclass
import json


@dataclass
class GroupConfig:
    """Configuration for a Cognito User Pool Group"""
    group_name: str
    description: str
    precedence: int
    role_arn: Optional[str] = None


class CognitoConfigService:
    """
    Service for managing AWS Cognito User Pool configuration and groups.
    
    This service handles:
    - User Pool configuration validation
    - Group management and IAM role setup
    - Connection validation to AWS Cognito
    """
    
    def __init__(self, user_pool_id: str, client_id: str, region: str = 'us-east-1'):
        """
        Initialize the Cognito Configuration Service.
        
        Args:
            user_pool_id: AWS Cognito User Pool ID
            client_id: AWS Cognito App Client ID
            region: AWS region for Cognito service
        """
        self.user_pool_id = user_pool_id
        self.client_id = client_id
        self.region = region
        self.logger = logging.getLogger(__name__)
        
        try:
            self.cognito_client = boto3.client('cognito-idp', region_name=region)
            self.iam_client = boto3.client('iam', region_name=region)
        except NoCredentialsError:
            self.logger.error("AWS credentials not found")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize AWS clients: {str(e)}")
            raise
    
    def get_user_pool_config(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve the current User Pool configuration.
        
        Returns:
            Dictionary containing User Pool configuration or None if error
        """
        try:
            response = self.cognito_client.describe_user_pool(
                UserPoolId=self.user_pool_id
            )
            return response.get('UserPool', {})
        except ClientError as e:
            self.logger.error(f"Failed to get user pool config: {e.response['Error']['Message']}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error getting user pool config: {str(e)}")
            return None
    
    def validate_cognito_connection(self) -> bool:
        """
        Validate connection to AWS Cognito service.
        
        Returns:
            True if connection is valid, False otherwise
        """
        try:
            # Test connection by describing the user pool
            response = self.cognito_client.describe_user_pool(
                UserPoolId=self.user_pool_id
            )
            
            # Validate that the app client exists
            clients_response = self.cognito_client.list_user_pool_clients(
                UserPoolId=self.user_pool_id
            )
            
            client_exists = any(
                client['ClientId'] == self.client_id 
                for client in clients_response.get('UserPoolClients', [])
            )
            
            if not client_exists:
                self.logger.error(f"App client {self.client_id} not found in user pool")
                return False
            
            self.logger.info("Cognito connection validated successfully")
            return True
            
        except ClientError as e:
            self.logger.error(f"Cognito connection validation failed: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error validating Cognito connection: {str(e)}")
            return False
    
    def setup_user_pool_groups(self, groups: List[GroupConfig]) -> bool:
        """
        Create or update User Pool groups with specified configurations.
        
        Args:
            groups: List of GroupConfig objects defining the groups to create
            
        Returns:
            True if all groups were created/updated successfully, False otherwise
        """
        success_count = 0
        
        for group_config in groups:
            try:
                # Check if group already exists
                existing_groups = self._list_existing_groups()
                group_exists = group_config.group_name in existing_groups
                
                if group_exists:
                    # Update existing group
                    self._update_group(group_config)
                    self.logger.info(f"Updated group: {group_config.group_name}")
                else:
                    # Create new group
                    self._create_group(group_config)
                    self.logger.info(f"Created group: {group_config.group_name}")
                
                success_count += 1
                
            except ClientError as e:
                self.logger.error(f"Failed to setup group {group_config.group_name}: {e.response['Error']['Message']}")
            except Exception as e:
                self.logger.error(f"Unexpected error setting up group {group_config.group_name}: {str(e)}")
        
        return success_count == len(groups)
    
    def create_user_pool_if_not_exists(self) -> Optional[str]:
        """
        Create a new User Pool if it doesn't exist.
        
        Returns:
            User Pool ID if created or already exists, None if error
        """
        try:
            # First check if the user pool already exists
            if self.validate_cognito_connection():
                self.logger.info(f"User Pool {self.user_pool_id} already exists")
                return self.user_pool_id
            
            # Create new user pool
            response = self.cognito_client.create_user_pool(
                PoolName='icode-user-pool',
                Policies={
                    'PasswordPolicy': {
                        'MinimumLength': 8,
                        'RequireUppercase': True,
                        'RequireLowercase': True,
                        'RequireNumbers': True,
                        'RequireSymbols': False
                    }
                },
                AutoVerifiedAttributes=['email'],
                UsernameAttributes=['email'],
                Schema=[
                    {
                        'Name': 'email',
                        'AttributeDataType': 'String',
                        'Required': True,
                        'Mutable': True
                    }
                ]
            )
            
            new_user_pool_id = response['UserPool']['Id']
            self.logger.info(f"Created new User Pool: {new_user_pool_id}")
            return new_user_pool_id
            
        except ClientError as e:
            self.logger.error(f"Failed to create user pool: {e.response['Error']['Message']}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error creating user pool: {str(e)}")
            return None
    
    def configure_user_pool_policies(self) -> bool:
        """
        Configure User Pool policies for security and compliance.
        
        Returns:
            True if policies were configured successfully, False otherwise
        """
        try:
            self.cognito_client.update_user_pool(
                UserPoolId=self.user_pool_id,
                Policies={
                    'PasswordPolicy': {
                        'MinimumLength': 8,
                        'RequireUppercase': True,
                        'RequireLowercase': True,
                        'RequireNumbers': True,
                        'RequireSymbols': False
                    }
                },
                AccountRecoverySetting={
                    'RecoveryMechanisms': [
                        {
                            'Priority': 1,
                            'Name': 'verified_email'
                        }
                    ]
                },
                UserPoolAddOns={
                    'AdvancedSecurityMode': 'ENFORCED'
                }
            )
            
            self.logger.info("User Pool policies configured successfully")
            return True
            
        except ClientError as e:
            self.logger.error(f"Failed to configure user pool policies: {e.response['Error']['Message']}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error configuring user pool policies: {str(e)}")
            return False
    
    def setup_group_iam_roles(self, group_mappings: Dict[str, str]) -> bool:
        """
        Setup IAM roles for Cognito groups.
        
        Args:
            group_mappings: Dictionary mapping group names to IAM role ARNs
            
        Returns:
            True if all IAM roles were setup successfully, False otherwise
        """
        success_count = 0
        
        for group_name, role_arn in group_mappings.items():
            try:
                # Validate that the IAM role exists
                if not self._validate_iam_role(role_arn):
                    self.logger.error(f"IAM role {role_arn} does not exist")
                    continue
                
                # Update the group with the IAM role
                self.cognito_client.update_group(
                    GroupName=group_name,
                    UserPoolId=self.user_pool_id,
                    RoleArn=role_arn
                )
                
                self.logger.info(f"Assigned IAM role {role_arn} to group {group_name}")
                success_count += 1
                
            except ClientError as e:
                self.logger.error(f"Failed to setup IAM role for group {group_name}: {e.response['Error']['Message']}")
            except Exception as e:
                self.logger.error(f"Unexpected error setting up IAM role for group {group_name}: {str(e)}")
        
        return success_count == len(group_mappings)
    
    def _list_existing_groups(self) -> List[str]:
        """List existing groups in the User Pool."""
        try:
            response = self.cognito_client.list_groups(
                UserPoolId=self.user_pool_id
            )
            return [group['GroupName'] for group in response.get('Groups', [])]
        except ClientError:
            return []
    
    def _create_group(self, group_config: GroupConfig) -> None:
        """Create a new group in the User Pool."""
        params = {
            'GroupName': group_config.group_name,
            'UserPoolId': self.user_pool_id,
            'Description': group_config.description,
            'Precedence': group_config.precedence
        }
        
        if group_config.role_arn:
            params['RoleArn'] = group_config.role_arn
        
        self.cognito_client.create_group(**params)
    
    def _update_group(self, group_config: GroupConfig) -> None:
        """Update an existing group in the User Pool."""
        params = {
            'GroupName': group_config.group_name,
            'UserPoolId': self.user_pool_id,
            'Description': group_config.description,
            'Precedence': group_config.precedence
        }
        
        if group_config.role_arn:
            params['RoleArn'] = group_config.role_arn
        
        self.cognito_client.update_group(**params)
    
    def _validate_iam_role(self, role_arn: str) -> bool:
        """Validate that an IAM role exists."""
        try:
            role_name = role_arn.split('/')[-1]
            self.iam_client.get_role(RoleName=role_name)
            return True
        except ClientError:
            return False