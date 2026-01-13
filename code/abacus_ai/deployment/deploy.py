"""
Deployment Script for Abacus.AI Models with Token Management
"""

import os
import logging
import json
import time
import requests
import hashlib
import base64
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
import docker
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TokenManager:
    """Manage authentication tokens for Abacus.AI deployment"""
    
    def __init__(self, secret_name: str = "abacus-ai-tokens"):
        """
        Initialize token manager
        
        Args:
            secret_name: AWS Secrets Manager secret name
        """
        self.secret_name = secret_name
        self.session = boto3.session.Session()
        self.secrets_manager = self.session.client('secretsmanager')
        
    def get_api_key(self, environment: str = "production") -> str:
        """Get API key from environment or secrets manager"""
        # Try environment variable first
        env_var = f"ABACUS_AI_API_KEY_{environment.upper()}"
        api_key = os.getenv(env_var)
        
        if api_key:
            logger.info(f"Using API key from environment variable: {env_var}")
            return api_key
        
        # Try AWS Secrets Manager
        try:
            secret_id = f"{self.secret_name}/api_key/{environment}"
            response = self.secrets_manager.get_secret_value(SecretId=secret_id)
            api_key = response['SecretString']
            logger.info(f"Retrieved API key from AWS Secrets Manager: {secret_id}")
            return api_key
        except ClientError as e:
            logger.error(f"Failed to retrieve API key from AWS Secrets Manager: {str(e)}")
            raise ValueError(f"Could not retrieve API key for environment: {environment}")
    
    def store_api_key(self, api_key: str, environment: str = "production"):
        """Store API key in AWS Secrets Manager"""
        secret_id = f"{self.secret_name}/api_key/{environment}"
        
        try:
            # Try to create secret first
            self.secrets_manager.create_secret(
                Name=secret_id,
                SecretString=api_key,
                Description=f"Abacus.AI API key for {environment} environment"
            )
            logger.info(f"API key stored in AWS Secrets Manager: {secret_id}")
        except self.secrets_manager.exceptions.ResourceExistsException:
            # Update existing secret
            self.secrets_manager.update_secret(
                SecretId=secret_id,
                SecretString=api_key
            )
            logger.info(f"API key updated in AWS Secrets Manager: {secret_id}")
        except ClientError as e:
            logger.error(f"Failed to store API key: {str(e)}")
            raise
    
    def rotate_api_key(self, environment: str = "production") -> str:
        """Rotate API key and return new key"""
        new_key = self._generate_api_key()
        self.store_api_key(new_key, environment)
        logger.info(f"API key rotated for {environment} environment")
        return new_key
    
    def _generate_api_key(self) -> str:
        """Generate a new API key"""
        timestamp = str(int(time.time()))
        random_data = os.urandom(16)
        data = timestamp.encode() + random_data
        hash_obj = hashlib.sha256(data)
        return base64.b64encode(hash_obj.digest()).decode()[:32]


class ModelDeployer:
    """Deploy models to Abacus.AI platform"""
    
    def __init__(self, token_manager: TokenManager, base_url: str = "https://api.abacus.ai"):
        """
        Initialize model deployer
        
        Args:
            token_manager: Token manager instance
            base_url: Abacus.AI API base URL
        """
        self.token_manager = token_manager
        self.base_url = base_url
        self.session = requests.Session()
        self._setup_session()
        
    def _setup_session(self):
        """Setup HTTP session with authentication"""
        def get_api_key():
            return self.token_manager.get_api_key()
        
        # Update session headers and auth
        self.session.headers.update({
            'Authorization': f'Bearer {get_api_key()}',
            'Content-Type': 'application/json',
            'User-Agent': 'AbacusAI-Deployer/1.0'
        })
        
        # Add token refresh interceptor
        original_request = self.session.request
        
        def auth_request(method, url, **kwargs):
            response = original_request(method, url, **kwargs)
            
            # Handle token expiration
            if response.status_code == 401:
                logger.info("Token expired, refreshing...")
                self.token_manager.rotate_api_key()
                self.session.headers['Authorization'] = f'Bearer {get_api_key()}'
                response = original_request(method, url, **kwargs)
            
            return response
        
        self.session.request = auth_request
    
    def deploy_model(self, model_path: str, model_config: Dict[str, Any], 
                    environment: str = "production") -> Dict[str, Any]:
        """
        Deploy model to Abacus.AI
        
        Args:
            model_path: Path to model file
            model_config: Model configuration
            environment: Deployment environment
            
        Returns:
            Deployment details
        """
        logger.info(f"Deploying model to {environment} environment")
        
        # Upload model file
        model_id = self._upload_model(model_path, model_config, environment)
        
        # Create deployment
        deployment_config = {
            "model_id": model_id,
            "version": model_config.get("version", "v1.0"),
            "environment": environment,
            "scaling": model_config.get("scaling", {"min_instances": 1, "max_instances": 10}),
            "resources": model_config.get("resources", {"cpu": "1", "memory": "2Gi"}),
            "deployment_timestamp": datetime.utcnow().isoformat()
        }
        
        deployment_result = self._create_deployment(deployment_config)
        
        # Wait for deployment to be ready
        self._wait_for_deployment(deployment_result["deployment_id"])
        
        logger.info(f"Model deployed successfully: {deployment_result['deployment_id']}")
        return deployment_result
    
    def _upload_model(self, model_path: str, model_config: Dict[str, Any], 
                     environment: str) -> str:
        """Upload model to Abacus.AI storage"""
        
        # Prepare upload request
        with open(model_path, 'rb') as f:
            files = {'model': (os.path.basename(model_path), f, 'application/octet-stream')}
            
            metadata = {
                "name": model_config["name"],
                "version": model_config.get("version", "v1.0"),
                "algorithm": model_config.get("algorithm", "unknown"),
                "features": model_config.get("features", []),
                "target": model_config.get("target", "unknown"),
                "environment": environment,
                "upload_timestamp": datetime.utcnow().isoformat()
            }
            
            headers = {'X-Model-Metadata': json.dumps(metadata)}
            
            # Upload model
            upload_url = f"{self.base_url}/models/upload"
            response = self.session.post(upload_url, files=files, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Model upload failed: {response.text}")
            
            result = response.json()
            return result["model_id"]
    
    def _create_deployment(self, deployment_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create model deployment"""
        endpoint = "/deployments"
        response = self.session.post(self.base_url + endpoint, json=deployment_config)
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Deployment creation failed: {response.text}")
        
        return response.json()
    
    def _wait_for_deployment(self, deployment_id: str, timeout: int = 600, 
                           check_interval: int = 30) -> None:
        """Wait for deployment to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self._get_deployment_status(deployment_id)
            
            if status["state"] == "READY":
                logger.info("Deployment is ready")
                return
            elif status["state"] == "FAILED":
                raise Exception(f"Deployment failed: {status.get('error', 'Unknown error')}")
            
            logger.info(f"Deployment status: {status['state']}, waiting...")
            time.sleep(check_interval)
        
        raise TimeoutError(f"Deployment did not complete within {timeout} seconds")
    
    def _get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Get deployment status"""
        endpoint = f"/deployments/{deployment_id}/status"
        response = self.session.get(self.base_url + endpoint)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get deployment status: {response.text}")
        
        return response.json()
    
    def scale_deployment(self, deployment_id: str, min_instances: int, max_instances: int):
        """Scale deployment"""
        endpoint = f"/deployments/{deployment_id}/scale"
        data = {"min_instances": min_instances, "max_instances": max_instances}
        
        response = self.session.post(self.base_url + endpoint, json=data)
        
        if response.status_code != 200:
            raise Exception(f"Failed to scale deployment: {response.text}")
        
        return response.json()
    
    def rollback_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Rollback deployment to previous version"""
        endpoint = f"/deployments/{deployment_id}/rollback"
        response = self.session.post(self.base_url + endpoint)
        
        if response.status_code != 200:
            raise Exception(f"Failed to rollback deployment: {response.text}")
        
        return response.json()
    
    def delete_deployment(self, deployment_id: str):
        """Delete deployment"""
        endpoint = f"/deployments/{deployment_id}"
        response = self.session.delete(self.base_url + endpoint)
        
        if response.status_code != 204:
            raise Exception(f"Failed to delete deployment: {response.text}")
        
        logger.info(f"Deployment {deployment_id} deleted successfully")


class DockerModelService:
    """Containerize model as Docker service for Abacus.AI deployment"""
    
    def __init__(self, model_path: str, service_name: str = "abacus-model"):
        """
        Initialize Docker service builder
        
        Args:
            model_path: Path to model file
            service_name: Name of the Docker service
        """
        self.model_path = Path(model_path)
        self.service_name = service_name
        self.docker_client = docker.from_env()
    
    def create_dockerfile(self, output_dir: Path, requirements: List[str] = None):
        """Create Dockerfile for model service"""
        requirements = requirements or [
            "fastapi==0.104.1",
            "uvicorn==0.24.0",
            "pandas==2.1.3",
            "numpy==1.24.3",
            "scikit-learn==1.3.2",
            "joblib==1.3.2",
            "redis==5.0.1",
            "aiohttp==3.9.1",
            "boto3==1.34.0"
        ]
        
        dockerfile_content = f"""
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    g++ \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and model
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash modeluser \\
    && chown -R modeluser:modeluser /app
USER modeluser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "model_service:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        
        requirements_content = "\n".join(requirements)
        
        # Write Dockerfile
        dockerfile_path = output_dir / "Dockerfile"
        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)
        
        # Write requirements.txt
        requirements_path = output_dir / "requirements.txt"
        with open(requirements_path, 'w') as f:
            f.write(requirements_content)
        
        logger.info(f"Docker files created in {output_dir}")
        return dockerfile_path
    
    def build_image(self, output_dir: Path, tag: str = None) -> str:
        """Build Docker image"""
        tag = tag or f"{self.service_name}:latest"
        
        logger.info(f"Building Docker image: {tag}")
        
        image, build_logs = self.docker_client.images.build(
            path=str(output_dir),
            tag=tag,
            rm=True,
            pull=True
        )
        
        logger.info(f"Docker image built successfully: {tag}")
        return tag
    
    def push_image(self, image_tag: str, registry: str = None):
        """Push Docker image to registry"""
        if not registry:
            registry = os.getenv("DOCKER_REGISTRY", "docker.io")
        
        image_name = f"{registry}/{self.service_name}"
        tagged_image = f"{image_name}:latest"
        
        # Tag image
        self.docker_client.api.tag(image_tag, image_name, tag="latest")
        
        # Push image
        logger.info(f"Pushing Docker image to {registry}")
        self.docker_client.images.push(image_name, tag="latest")
        
        logger.info(f"Docker image pushed successfully: {image_name}")
        return image_name


def main():
    """Main deployment script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy Abacus.AI models")
    parser.add_argument("--model-path", required=True, help="Path to model file")
    parser.add_argument("--config", required=True, help="Model configuration JSON file")
    parser.add_argument("--environment", default="production", help="Deployment environment")
    parser.add_argument("--create-docker", action="store_true", help="Create Docker container")
    parser.add_argument("--docker-tag", help="Docker image tag")
    parser.add_argument("--scale", type=int, nargs=2, metavar=('MIN', 'MAX'), 
                       help="Scale deployment to min and max instances")
    
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        model_config = json.load(f)
    
    # Initialize components
    token_manager = TokenManager()
    deployer = ModelDeployer(token_manager)
    
    try:
        # Deploy model
        deployment_result = deployer.deploy_model(
            args.model_path, 
            model_config, 
            args.environment
        )
        
        print(f"✅ Model deployed successfully!")
        print(f"Deployment ID: {deployment_result['deployment_id']}")
        print(f"Endpoint: {deployment_result.get('endpoint', 'N/A')}")
        
        # Scale if requested
        if args.scale:
            min_inst, max_inst = args.scale
            scaling_result = deployer.scale_deployment(
                deployment_result['deployment_id'], 
                min_inst, 
                max_inst
            )
            print(f"✅ Deployment scaled to {min_inst}-{max_inst} instances")
        
        # Create Docker container if requested
        if args.create_docker:
            service = DockerModelService(args.model_path)
            output_dir = Path("docker_output")
            output_dir.mkdir(exist_ok=True)
            
            # Create Dockerfile
            service.create_dockerfile(output_dir)
            
            # Build image
            image_tag = service.build_image(output_dir, args.docker_tag)
            
            # Push if registry is configured
            if os.getenv("DOCKER_REGISTRY"):
                service.push_image(image_tag)
        
        # Save deployment details
        deployment_file = f"deployment_{args.environment}_{int(time.time())}.json"
        with open(deployment_file, 'w') as f:
            json.dump(deployment_result, f, indent=2)
        
        print(f"✅ Deployment details saved to {deployment_file}")
        
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()