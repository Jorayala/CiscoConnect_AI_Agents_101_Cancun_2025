import httpx
import asyncio
import os
import time
import json
import hashlib
import base64
from datetime import datetime, timezone
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from dotenv import load_dotenv
import logging

# Load .env file for credentials
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("IntersightMCP")

class IntersightAuthManager:
    """
    Authentication manager for Cisco Intersight API
    Uses RSA signature-based authentication
    """
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IntersightAuthManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self):
        if self._initialized:
            logger.info("IntersightAuthManager already initialized.")
            return

        async with self._lock:
            if self._initialized:
                return

            logger.info("IntersightAuthManager initializing...")
            self.base_url = os.getenv("INTERSIGHT_BASE_URL", "https://intersight.com")
            self.api_key_id = os.getenv("INTERSIGHT_API_KEY")
            self.private_key_content = os.getenv("INTERSIGHT_SECRET_KEY")
            
            if not self.api_key_id or not self.private_key_content:
                logger.error("WARNING: INTERSIGHT_API_KEY or INTERSIGHT_SECRET_KEY not set. Authentication will fail.")
                return
            
            # Load the private key (handle escaped newlines)
            try:
                # Replace escaped newlines with actual newlines
                private_key_pem = self.private_key_content.replace('\\n', '\n')
                
                self.private_key = serialization.load_pem_private_key(
                    private_key_pem.encode('utf-8'),
                    password=None,
                )
                logger.info("Successfully loaded Intersight private key.")
            except Exception as e:
                logger.error(f"Failed to load private key: {e}")
                return

            # Create HTTP client with SSL verification
            self._client = httpx.AsyncClient(verify=True, timeout=30.0)
            self._initialized = True
            logger.info(f"IntersightAuthManager initialized. Base URL: {self.base_url}")

    def _generate_signature(self, method: str, path: str, body: str = "") -> tuple:
        """
        Generate RSA signature for Intersight API request
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            body: Request body (for POST/PATCH requests)
            
        Returns:
            tuple: (signature, timestamp)
        """
        # Create timestamp in RFC1123 format (required by Intersight)
        timestamp = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Calculate content digest (required for all requests in Intersight)
        if not body:
            body = ""  # Empty body for GET requests
        body_hash = hashlib.sha256(body.encode('utf-8')).digest()
        content_digest = base64.b64encode(body_hash).decode('utf-8')
        
        # Create string to sign (must include digest for all requests)
        string_to_sign = f"(request-target): {method.lower()} {path}\n"
        string_to_sign += f"date: {timestamp}\n"
        string_to_sign += f"host: intersight.com\n"
        string_to_sign += f"digest: SHA-256={content_digest}"
        
        # Sign the string
        signature = self.private_key.sign(
            string_to_sign.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        # Encode signature
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return signature_b64, timestamp

    def _get_auth_headers(self, method: str, path: str, body: str = "") -> dict:
        """
        Generate authentication headers for Intersight API request
        
        Args:
            method: HTTP method
            path: API path  
            body: Request body
            
        Returns:
            dict: Authentication headers
        """
        signature, timestamp = self._generate_signature(method, path, body)
        
        # Calculate content digest for headers (same as used in signature)
        if not body:
            body = ""
        body_hash = hashlib.sha256(body.encode('utf-8')).digest()
        content_digest = base64.b64encode(body_hash).decode('utf-8')
        
        # Build authorization header (always include digest for Intersight)
        auth_header = f'Signature keyId="{self.api_key_id}",'
        auth_header += f'algorithm="rsa-sha256",'
        auth_header += f'headers="(request-target) date host digest",'
        auth_header += f'signature="{signature}"'
        
        headers = {
            'Authorization': auth_header,
            'Date': timestamp,
            'Host': 'intersight.com',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Digest': f'SHA-256={content_digest}'
        }
        
        return headers

    async def get_authenticated_client(self) -> httpx.AsyncClient:
        """
        Returns an httpx.AsyncClient instance configured for Intersight API
        """
        await self.initialize()
        return self._client

    async def make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """
        Make an authenticated request to Intersight API
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (e.g., '/api/v1/compute/PhysicalSummaries')
            data: Request payload for POST/PATCH requests
            
        Returns:
            dict: API response
        """
        await self.initialize()
        
        if not self._initialized:
            raise RuntimeError("IntersightAuthManager not properly initialized")
        
        url = f"{self.base_url}{endpoint}"
        path = endpoint
        body = ""
        
        if data:
            body = json.dumps(data)
        
        headers = self._get_auth_headers(method, path, body)
        
        try:
            if method.upper() == 'GET':
                response = await self._client.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = await self._client.post(url, headers=headers, content=body)
            elif method.upper() == 'PATCH':
                response = await self._client.patch(url, headers=headers, content=body)
            elif method.upper() == 'DELETE':
                response = await self._client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            if response.content:
                return response.json()
            else:
                return {"status": "success"}
                
        except httpx.HTTPStatusError as e:
            error_details = e.response.text
            try:
                error_details = json.dumps(e.response.json(), indent=2)
            except json.JSONDecodeError:
                pass
            logger.error(f"Intersight API Error (HTTP Status {e.response.status_code}): {error_details}")
            raise RuntimeError(f"Intersight API request failed: {e.response.text}") from e
        except httpx.RequestError as e:
            logger.error(f"Network Error during Intersight API request: {e}")
            raise RuntimeError(f"Intersight API request failed due to network error: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred during Intersight API request: {e}")
            raise RuntimeError(f"Intersight API request failed: {e}") from e

# Global instance
intersight_auth_manager = IntersightAuthManager()
