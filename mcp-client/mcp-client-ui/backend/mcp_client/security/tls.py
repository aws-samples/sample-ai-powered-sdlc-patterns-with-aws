"""
TLS/SSL security utilities for the MCP Client.
"""

import logging
import os
import ssl
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


class TLSVersion(Enum):
    """Supported TLS versions."""
    
    TLS_1_0 = "TLSv1"
    TLS_1_1 = "TLSv1.1"
    TLS_1_2 = "TLSv1.2"
    TLS_1_3 = "TLSv1.3"
    
    @classmethod
    def get_default(cls) -> "TLSVersion":
        """Get the default TLS version (highest available)."""
        # Use the highest available version
        return cls.TLS_1_2  # Default to TLS 1.2 for compatibility


class CertificateVerificationMode(Enum):
    """Certificate verification modes."""
    
    NONE = "none"  # No verification (insecure)
    REQUIRED = "required"  # Verify certificate is valid
    HOSTNAME = "hostname"  # Verify certificate and hostname match
    FINGERPRINT = "fingerprint"  # Verify certificate fingerprint matches expected value


@dataclass
class TLSConfig:
    """Configuration for TLS/SSL connections."""
    
    # Whether to use TLS/SSL
    enabled: bool = True
    
    # Minimum TLS version to use
    min_version: TLSVersion = TLSVersion.TLS_1_2
    
    # Certificate verification mode
    verification_mode: CertificateVerificationMode = CertificateVerificationMode.HOSTNAME
    
    # Path to CA certificate file or directory
    ca_cert_path: Optional[str] = None
    
    # Path to client certificate file
    client_cert_path: Optional[str] = None
    
    # Path to client private key file
    client_key_path: Optional[str] = None
    
    # Password for client private key file
    client_key_password: Optional[str] = None
    
    # Expected certificate fingerprints for certificate pinning
    # Format: {hostname: fingerprint}
    cert_fingerprints: Dict[str, str] = None
    
    # Cipher suites to use (None for default)
    cipher_suites: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.cert_fingerprints is None:
            self.cert_fingerprints = {}


def create_ssl_context(config: TLSConfig) -> ssl.SSLContext:
    """
    Create an SSL context from the given configuration.
    
    Args:
        config: TLS configuration
        
    Returns:
        ssl.SSLContext: The configured SSL context
        
    Raises:
        ValueError: If the configuration is invalid
    """
    if not config.enabled:
        logger.warning("TLS is disabled, returning None for SSL context")
        return None
        
    # Create the SSL context
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    
    # Set minimum TLS version
    if config.min_version == TLSVersion.TLS_1_3:
        context.minimum_version = ssl.TLSVersion.TLSv1_3
    elif config.min_version == TLSVersion.TLS_1_2:
        context.minimum_version = ssl.TLSVersion.TLSv1_2
    elif config.min_version == TLSVersion.TLS_1_1:
        context.minimum_version = ssl.TLSVersion.TLSv1_1
    elif config.min_version == TLSVersion.TLS_1_0:
        context.minimum_version = ssl.TLSVersion.TLSv1
    
    # Set verification mode
    if config.verification_mode == CertificateVerificationMode.NONE:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        logger.warning("TLS certificate verification is disabled")
    elif config.verification_mode == CertificateVerificationMode.REQUIRED:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        logger.info("TLS certificate verification is required")
    elif config.verification_mode == CertificateVerificationMode.HOSTNAME:
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        logger.info("TLS certificate and hostname verification is required")
    elif config.verification_mode == CertificateVerificationMode.FINGERPRINT:
        # For fingerprint verification, we still need to verify the certificate
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        logger.info("TLS certificate fingerprint verification is required")
        
        if not config.cert_fingerprints:
            raise ValueError("Certificate fingerprints are required for fingerprint verification")
            
    # Load CA certificates
    if config.ca_cert_path:
        if os.path.isdir(config.ca_cert_path):
            context.load_verify_locations(capath=config.ca_cert_path)
            logger.info(f"Loaded CA certificates from directory: {config.ca_cert_path}")
        elif os.path.isfile(config.ca_cert_path):
            context.load_verify_locations(cafile=config.ca_cert_path)
            logger.info(f"Loaded CA certificate from file: {config.ca_cert_path}")
        else:
            raise ValueError(f"CA certificate path does not exist: {config.ca_cert_path}")
    else:
        # Load default CA certificates
        context.load_default_certs(purpose=ssl.Purpose.SERVER_AUTH)
        logger.info("Loaded default CA certificates")
        
    # Load client certificate and key for mutual TLS
    if config.client_cert_path:
        if not os.path.isfile(config.client_cert_path):
            raise ValueError(f"Client certificate file does not exist: {config.client_cert_path}")
            
        if not config.client_key_path:
            raise ValueError("Client key path is required when client certificate is provided")
            
        if not os.path.isfile(config.client_key_path):
            raise ValueError(f"Client key file does not exist: {config.client_key_path}")
            
        try:
            context.load_cert_chain(
                certfile=config.client_cert_path,
                keyfile=config.client_key_path,
                password=config.client_key_password,
            )
            logger.info(f"Loaded client certificate from {config.client_cert_path}")
        except (FileNotFoundError, ssl.SSLError) as e:
            raise ValueError(f"Failed to load client certificate: {e}")
            
    # Set cipher suites if specified
    if config.cipher_suites:
        try:
            context.set_ciphers(config.cipher_suites)
            logger.info(f"Set cipher suites: {config.cipher_suites}")
        except ssl.SSLError as e:
            raise ValueError(f"Invalid cipher suites: {e}")
            
    # Set secure protocol options
    # Disable insecure protocols and features
    context.options |= ssl.OP_NO_COMPRESSION
    
    # Note: We don't need to set OP_NO_SSLv2, OP_NO_SSLv3, etc. anymore
    # as we're using the minimum_version property instead
            
    return context


def verify_certificate_fingerprint(
    ssl_socket: ssl.SSLSocket, hostname: str, fingerprints: Dict[str, str]
) -> bool:
    """
    Verify that the certificate fingerprint matches the expected value.
    
    Args:
        ssl_socket: The SSL socket to verify
        hostname: The hostname to check against
        fingerprints: Dictionary mapping hostnames to expected fingerprints
        
    Returns:
        bool: True if the fingerprint matches, False otherwise
    """
    if hostname not in fingerprints:
        logger.warning(f"No fingerprint found for hostname: {hostname}")
        return False
        
    expected_fingerprint = fingerprints[hostname]
    cert = ssl_socket.getpeercert(binary_form=True)
    if not cert:
        logger.warning("No certificate received from peer")
        return False
        
    # Calculate the fingerprint
    import hashlib
    fingerprint = hashlib.sha256(cert).hexdigest()
    
    if fingerprint.lower() == expected_fingerprint.lower():
        logger.debug(f"Certificate fingerprint verified for {hostname}")
        return True
    else:
        logger.warning(
            f"Certificate fingerprint mismatch for {hostname}: "
            f"expected {expected_fingerprint}, got {fingerprint}"
        )
        return False


class CertificateVerifier:
    """Certificate verifier for SSL connections."""
    
    def __init__(self, config: TLSConfig):
        """
        Initialize the certificate verifier.
        
        Args:
            config: TLS configuration
        """
        self.config = config
        
    def verify_hostname(self, ssl_socket: ssl.SSLSocket, hostname: str) -> bool:
        """
        Verify the hostname against the certificate.
        
        Args:
            ssl_socket: The SSL socket to verify
            hostname: The hostname to check against
            
        Returns:
            bool: True if the hostname is valid, False otherwise
        """
        try:
            cert = ssl_socket.getpeercert()
            if not cert:
                logger.warning("No certificate received from peer")
                return False
                
            # Check for subjectAltName
            san = cert.get("subjectAltName", [])
            for key, value in san:
                if key == "DNS" and self._match_hostname(value, hostname):
                    return True
                    
            # Check for commonName in subject
            if "subject" in cert:
                for key, value in cert["subject"]:
                    if key == "commonName" and self._match_hostname(value, hostname):
                        return True
                        
            logger.warning(f"Certificate hostname verification failed: {hostname} not found in certificate")
            return False
        except Exception as e:
            logger.warning(f"Certificate hostname verification failed: {e}")
            return False
            
    def _match_hostname(self, cert_hostname: str, hostname: str) -> bool:
        """
        Match a hostname against a certificate hostname.
        
        Args:
            cert_hostname: The hostname from the certificate
            hostname: The hostname to check against
            
        Returns:
            bool: True if the hostname matches, False otherwise
        """
        # Simple exact match
        if cert_hostname == hostname:
            return True
            
        # Wildcard match
        if cert_hostname.startswith("*."):
            domain = cert_hostname[2:]
            if hostname.endswith(domain) and hostname.find(".") == hostname.find(domain) - 1:
                return True
                
        return False
            
    def verify_fingerprint(self, ssl_socket: ssl.SSLSocket, hostname: str) -> bool:
        """
        Verify the certificate fingerprint.
        
        Args:
            ssl_socket: The SSL socket to verify
            hostname: The hostname to check against
            
        Returns:
            bool: True if the fingerprint is valid, False otherwise
        """
        return verify_certificate_fingerprint(
            ssl_socket, hostname, self.config.cert_fingerprints
        )
        
    def verify(self, ssl_socket: ssl.SSLSocket, hostname: str) -> bool:
        """
        Verify the certificate according to the configured verification mode.
        
        Args:
            ssl_socket: The SSL socket to verify
            hostname: The hostname to check against
            
        Returns:
            bool: True if the certificate is valid, False otherwise
        """
        if self.config.verification_mode == CertificateVerificationMode.NONE:
            return True
        elif self.config.verification_mode == CertificateVerificationMode.REQUIRED:
            # The SSL context already verified the certificate
            return True
        elif self.config.verification_mode == CertificateVerificationMode.HOSTNAME:
            return self.verify_hostname(ssl_socket, hostname)
        elif self.config.verification_mode == CertificateVerificationMode.FINGERPRINT:
            return self.verify_fingerprint(ssl_socket, hostname)
        else:
            logger.warning(f"Unknown verification mode: {self.config.verification_mode}")
            return False