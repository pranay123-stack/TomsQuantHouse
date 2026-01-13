"""
Abacus.AI Python Client for Feature Group Creation and Data Upload
"""

import requests
import pandas as pd
import json
import time
import logging
from typing import Dict, List, Optional, Union
from datetime import datetime
import hashlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AbacusAIClient:
    """Client for interacting with Abacus.AI API"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.abacus.ai"):
        """
        Initialize Abacus.AI client
        
        Args:
            api_key: Abacus.AI API key
            base_url: Base URL for API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'AbacusAI-Python-Client/1.0'
        })
        
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                     params: Optional[Dict] = None, retries: int = 3) -> Dict:
        """
        Make API request with retry logic
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request data
            params: URL parameters
            retries: Number of retry attempts
            
        Returns:
            API response
        """
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(url, params=params)
                elif method.upper() == 'POST':
                    response = self.session.post(url, json=data, params=params)
                elif method.upper() == 'PUT':
                    response = self.session.put(url, json=data, params=params)
                elif method.upper() == 'DELETE':
                    response = self.session.delete(url, params=params)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"API request failed: {response.status_code} - {response.text}")
                    if attempt == retries - 1:
                        raise Exception(f"API request failed after {retries} attempts: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}): {str(e)}")
                if attempt == retries - 1:
                    raise
                time.sleep(1)
    
    def create_feature_group(self, name: str, description: str, 
                           schema: List[Dict], version: str = "v1") -> Dict:
        """
        Create a new feature group
        
        Args:
            name: Feature group name
            description: Description of the feature group
            schema: List of column schemas with name, type, and description
            version: Version identifier
            
        Returns:
            Created feature group details
        """
        endpoint = f"/feature-groups"
        payload = {
            "name": name,
            "description": description,
            "version": version,
            "schema": schema,
            "created_at": datetime.utcnow().isoformat()
        }
        
        try:
            result = self._make_request('POST', endpoint, data=payload)
            logger.info(f"Feature group '{name}' created successfully")
            return result
        except Exception as e:
            logger.error(f"Failed to create feature group '{name}': {str(e)}")
            raise
    
    def get_feature_group(self, feature_group_id: str) -> Dict:
        """
        Get feature group details
        
        Args:
            feature_group_id: Feature group identifier
            
        Returns:
            Feature group details
        """
        endpoint = f"/feature-groups/{feature_group_id}"
        return self._make_request('GET', endpoint)
    
    def list_feature_groups(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        List all feature groups
        
        Args:
            limit: Number of results to return
            offset: Number of results to skip
            
        Returns:
            List of feature groups
        """
        endpoint = "/feature-groups"
        params = {"limit": limit, "offset": offset}
        result = self._make_request('GET', endpoint, params=params)
        return result.get('feature_groups', [])
    
    def upload_data(self, feature_group_id: str, data: Union[pd.DataFrame, List[Dict]],
                   operation: str = "UPSERT", batch_size: int = 1000) -> Dict:
        """
        Upload data to feature group
        
        Args:
            feature_group_id: Feature group identifier
            data: Data to upload (DataFrame or list of dictionaries)
            operation: Operation type (UPSERT, INSERT, UPDATE)
            batch_size: Number of records per batch
            
        Returns:
            Upload result details
        """
        if isinstance(data, pd.DataFrame):
            data = data.to_dict('records')
        
        total_records = len(data)
        batches = [data[i:i + batch_size] for i in range(0, total_records, batch_size)]
        
        results = []
        
        for i, batch in enumerate(batches):
            logger.info(f"Uploading batch {i + 1}/{len(batches)} ({len(batch)} records)")
            
            endpoint = f"/feature-groups/{feature_group_id}/data"
            payload = {
                "operation": operation,
                "data": batch,
                "batch_id": hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8],
                "upload_timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                result = self._make_request('POST', endpoint, data=payload)
                results.append(result)
                logger.info(f"Batch {i + 1} uploaded successfully")
            except Exception as e:
                logger.error(f"Failed to upload batch {i + 1}: {str(e)}")
                raise
        
        return {
            "total_batches": len(batches),
            "total_records": total_records,
            "results": results
        }
    
    def validate_schema(self, data: pd.DataFrame, schema: List[Dict]) -> Dict:
        """
        Validate data against feature group schema
        
        Args:
            data: Data to validate
            schema: Target schema
            
        Returns:
            Validation results
        """
        issues = []
        
        for schema_field in schema:
            field_name = schema_field['name']
            field_type = schema_field['type']
            
            if field_name not in data.columns:
                issues.append(f"Missing required field: {field_name}")
                continue
            
            data_type = data[field_name].dtype
            
            # Type validation
            if field_type == 'string' and not pd.api.types.is_string_dtype(data_type):
                issues.append(f"Field '{field_name}' should be string but is {data_type}")
            elif field_type == 'integer' and not pd.api.types.is_integer_dtype(data_type):
                issues.append(f"Field '{field_name}' should be integer but is {data_type}")
            elif field_type == 'float' and not pd.api.types.is_numeric_dtype(data_type):
                issues.append(f"Field '{field_name}' should be numeric but is {data_type}")
            elif field_type == 'datetime' and not pd.api.types.is_datetime64_any_dtype(data_type):
                issues.append(f"Field '{field_name}' should be datetime but is {data_type}")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "field_count": len(schema),
            "data_shape": data.shape
        }