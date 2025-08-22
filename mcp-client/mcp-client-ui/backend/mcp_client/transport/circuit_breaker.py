"""
Circuit breaker implementation for the MCP Client.
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, cast

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """States of the circuit breaker."""

    CLOSED = "closed"  # Normal operation, requests are allowed
    OPEN = "open"  # Circuit is open, requests are not allowed
    HALF_OPEN = "half_open"  # Testing if the service is back online


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests are allowed
    - OPEN: Circuit is open, requests are not allowed
    - HALF_OPEN: Testing if the service is back online
    
    When the failure count exceeds the threshold, the circuit opens and
    remains open for the reset timeout. After the reset timeout, the circuit
    transitions to half-open and allows a single request. If the request
    succeeds, the circuit closes; if it fails, the circuit opens again.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        reset_timeout_seconds: float = 60.0,
        half_open_max_calls: int = 1,
        window_size_seconds: float = 60.0,
    ):
        """
        Initialize the circuit breaker.

        Args:
            failure_threshold: Number of failures before opening the circuit
            reset_timeout_seconds: Time to wait before transitioning from open to half-open
            half_open_max_calls: Maximum number of calls allowed in half-open state
            window_size_seconds: Time window for counting failures
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self.window_size_seconds = window_size_seconds
        
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time = 0.0
        self._open_time = 0.0
        self._half_open_calls = 0
        self._lock = asyncio.Lock()
        
        logger.info(
            f"Initialized circuit breaker with failure_threshold={failure_threshold}, "
            f"reset_timeout_seconds={reset_timeout_seconds}"
        )
        
    @property
    def state(self) -> CircuitState:
        """Get the current state of the circuit breaker."""
        return self._state
        
    @property
    def is_closed(self) -> bool:
        """Check if the circuit is closed."""
        return self._state == CircuitState.CLOSED
        
    @property
    def is_open(self) -> bool:
        """Check if the circuit is open."""
        return self._state == CircuitState.OPEN
        
    @property
    def is_half_open(self) -> bool:
        """Check if the circuit is half-open."""
        return self._state == CircuitState.HALF_OPEN
        
    @property
    def failures(self) -> int:
        """Get the current failure count."""
        return self._failures
        
    async def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: The function to execute
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function
            
        Raises:
            CircuitBreakerError: If the circuit is open
            Exception: Any exception raised by the function
        """
        async with self._lock:
            # Check if the circuit is open
            if self._state == CircuitState.OPEN:
                # Check if it's time to transition to half-open
                if time.time() - self._open_time >= self.reset_timeout_seconds:
                    logger.info("Circuit transitioning from OPEN to HALF_OPEN")
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                else:
                    # Circuit is still open
                    raise CircuitBreakerError(
                        f"Circuit is open, retry after {self._open_time + self.reset_timeout_seconds - time.time():.1f}s"
                    )
                    
            # Check if we've reached the maximum number of calls in half-open state
            if self._state == CircuitState.HALF_OPEN and self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerError("Maximum half-open calls reached")
                
            # Increment the half-open call count
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                
        # Execute the function
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Success, reset the circuit if needed
            async with self._lock:
                if self._state == CircuitState.HALF_OPEN:
                    logger.info("Circuit transitioning from HALF_OPEN to CLOSED")
                    self._state = CircuitState.CLOSED
                    self._failures = 0
                    
            return result
            
        except Exception as e:
            # Failure, update the circuit state
            async with self._lock:
                current_time = time.time()
                
                # Reset failure count if outside the window
                if current_time - self._last_failure_time > self.window_size_seconds:
                    self._failures = 0
                    
                # Increment failure count
                self._failures += 1
                self._last_failure_time = current_time
                
                # Check if we need to open the circuit
                if self._state == CircuitState.CLOSED and self._failures >= self.failure_threshold:
                    logger.warning(f"Circuit transitioning from CLOSED to OPEN after {self._failures} failures")
                    self._state = CircuitState.OPEN
                    self._open_time = current_time
                elif self._state == CircuitState.HALF_OPEN:
                    logger.warning("Circuit transitioning from HALF_OPEN to OPEN after failure")
                    self._state = CircuitState.OPEN
                    self._open_time = current_time
                    
            # Re-raise the exception
            raise
            
    def reset(self) -> None:
        """Reset the circuit breaker to its initial state."""
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time = 0.0
        self._open_time = 0.0
        self._half_open_calls = 0
        logger.info("Circuit breaker reset to CLOSED state")


class CircuitBreakerError(Exception):
    """Exception raised when the circuit breaker is open."""

    pass