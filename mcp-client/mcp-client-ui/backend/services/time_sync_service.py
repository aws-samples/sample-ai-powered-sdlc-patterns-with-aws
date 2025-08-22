"""
Time Synchronization Service for handling clock skew issues.

This service provides utilities for handling time synchronization issues
that can occur with JWT tokens, especially in containerized environments.
"""

import logging
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Optional


class TimeSyncService:
    """
    Service for handling time synchronization and clock skew issues.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._time_offset = None
        self._last_sync = None
        
    def get_synchronized_time(self) -> datetime:
        """
        Get current time with any known offset applied.
        
        Returns:
            Current datetime with synchronization offset applied
        """
        current_time = datetime.now(timezone.utc)
        
        if self._time_offset is not None:
            return current_time + self._time_offset
        
        return current_time
    
    def sync_with_ntp(self) -> bool:
        """
        Synchronize time with NTP server to detect clock skew.
        
        Returns:
            True if synchronization was successful, False otherwise
        """
        try:
            # Try multiple time sources
            time_sources = [
                'https://worldtimeapi.org/api/timezone/UTC',
                'http://worldtimeapi.org/api/timezone/UTC'
            ]
            
            for url in time_sources:
                try:
                    response = requests.get(url, timeout=3)
                    
                    if response.status_code == 200:
                        data = response.json()
                        server_time_str = data.get('utc_datetime')
                        
                        if server_time_str:
                            # Parse server time
                            server_time = datetime.fromisoformat(
                                server_time_str.replace('Z', '+00:00')
                            )
                            
                            # Calculate offset
                            local_time = datetime.now(timezone.utc)
                            self._time_offset = server_time - local_time
                            self._last_sync = local_time
                            
                            if abs(self._time_offset.total_seconds()) > 1:
                                self.logger.warning(
                                    f"Clock skew detected: {self._time_offset.total_seconds():.2f} seconds"
                                )
                            else:
                                self.logger.debug("Time synchronization successful")
                            
                            return True
                except Exception as e:
                    self.logger.debug(f"Failed to sync with {url}: {str(e)}")
                    continue
            
            # If external sync fails, assume no offset (use local time)
            self.logger.info("External time sync failed, using local system time")
            self._time_offset = timedelta(0)
            self._last_sync = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            self.logger.error(f"Time synchronization error: {str(e)}")
            # Fallback to no offset
            self._time_offset = timedelta(0)
            self._last_sync = datetime.now(timezone.utc)
            return True
    
    def get_clock_skew(self) -> Optional[timedelta]:
        """
        Get the current clock skew offset.
        
        Returns:
            timedelta representing clock skew, or None if not synchronized
        """
        return self._time_offset
    
    def should_resync(self) -> bool:
        """
        Check if time should be re-synchronized.
        
        Returns:
            True if re-synchronization is recommended
        """
        if self._last_sync is None:
            return True
        
        # Re-sync every hour
        return datetime.now(timezone.utc) - self._last_sync > timedelta(hours=1)
    
    def validate_token_time(self, iat: int, exp: int, leeway_seconds: int = 30) -> bool:
        """
        Validate token timestamps with clock skew consideration.
        
        Args:
            iat: Issued at timestamp
            exp: Expiration timestamp  
            leeway_seconds: Allowed clock skew in seconds
            
        Returns:
            True if token times are valid, False otherwise
        """
        try:
            current_time = self.get_synchronized_time()
            leeway = timedelta(seconds=leeway_seconds)
            
            # Check issued at time
            if iat:
                iat_time = datetime.fromtimestamp(iat, tz=timezone.utc)
                if iat_time > current_time + leeway:
                    self.logger.error(
                        f"Token issued in future: IAT={iat_time}, Current={current_time}"
                    )
                    return False
            
            # Check expiration time
            if exp:
                exp_time = datetime.fromtimestamp(exp, tz=timezone.utc)
                if exp_time <= current_time - leeway:
                    self.logger.error(
                        f"Token expired: EXP={exp_time}, Current={current_time}"
                    )
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating token time: {str(e)}")
            return False


# Global instance
time_sync_service = TimeSyncService()