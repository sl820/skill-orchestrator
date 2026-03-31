"""
Retry Policy and Backoff Strategies.
Handles retry logic with configurable backoff strategies.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
import time
import random


class BackoffStrategy(Enum):
    """Available backoff strategies."""
    FIXED = "FIXED"              # Fixed delay between retries
    LINEAR = "LINEAR"            # Linear increase: delay * attempt
    EXPONENTIAL = "EXPONENTIAL"  # Exponential: delay * (2 ** attempt)
    EXPONENTIAL_JITTER = "EXPONENTIAL_JITTER"  # Exponential with random jitter
    FIBONACCI = "FIBONACCI"      # Fibonacci backoff


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3              # Maximum number of attempts
    initial_delay_ms: float = 1000.0  # Initial delay in milliseconds
    max_delay_ms: float = 30000.0      # Maximum delay cap
    backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    retryable_errors: list[str] = field(default_factory=list)  # Errors that trigger retry
    fatal_errors: list[str] = field(default_factory=list)     # Errors that never retry
    on_retry: Optional[Callable] = None  # Callback on each retry

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Determine if an error should trigger a retry."""
        error_msg = str(error)

        # Check if fatal
        for fatal in self.fatal_errors:
            if fatal.lower() in error_msg.lower():
                return False

        # Check if retryable
        if self.retryable_errors:
            for retryable in self.retryable_errors:
                if retryable.lower() in error_msg.lower():
                    return attempt < self.max_attempts
            return False  # Error not in retryable list

        return attempt < self.max_attempts


@dataclass
class RetryState:
    """State tracked during retry attempts."""
    attempt: int = 0
    total_delay_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    started_at: Optional[float] = None
    last_attempt_at: Optional[float] = None


def calculate_backoff_delay(
    config: RetryConfig,
    attempt: int,
    base_delay_ms: float
) -> float:
    """
    Calculate delay for given attempt using configured backoff strategy.

    Args:
        config: Retry configuration
        attempt: Current attempt number (1-indexed)
        base_delay_ms: Base delay in milliseconds

    Returns:
        Delay in milliseconds for this attempt
    """
    if attempt <= 0:
        return base_delay_ms

    if config.backoff == BackoffStrategy.FIXED:
        delay = base_delay_ms

    elif config.backoff == BackoffStrategy.LINEAR:
        delay = base_delay_ms * attempt

    elif config.backoff == BackoffStrategy.EXPONENTIAL:
        delay = base_delay_ms * (2 ** (attempt - 1))

    elif config.backoff == BackoffStrategy.EXPONENTIAL_JITTER:
        exponential_delay = base_delay_ms * (2 ** (attempt - 1))
        # Add jitter: random value between 0 and half the delay
        jitter = random.random() * (exponential_delay * 0.5)
        delay = exponential_delay + jitter

    elif config.backoff == BackoffStrategy.FIBONACCI:
        # Fibonacci: F(n) = F(n-1) + F(n-2)
        fib_n_2 = 1  # F(1)
        fib_n_1 = 1  # F(2)
        for _ in range(attempt - 1):
            fib_current = fib_n_1 + fib_n_2
            fib_n_2 = fib_n_1
            fib_n_1 = fib_current
        delay = base_delay_ms * fib_n_1

    else:
        delay = base_delay_ms

    # Cap at max delay
    return min(delay, config.max_delay_ms)


async def execute_with_retry(
    func: Callable,
    config: RetryConfig,
    *args,
    **kwargs
):
    """
    Execute a function with retry logic.

    Args:
        func: Async function to execute
        config: Retry configuration
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Result of successful function execution

    Raises:
        Last exception if all retries exhausted
    """
    state = RetryState(started_at=time.time())
    last_error = None

    while state.attempt < config.max_attempts:
        state.attempt += 1
        state.last_attempt_at = time.time()

        try:
            result = await func(*args, **kwargs)
            return result

        except Exception as e:
            last_error = e
            state.errors.append(str(e))

            if not config.should_retry(e, state.attempt):
                raise

            # Calculate delay
            delay_ms = calculate_backoff_delay(
                config, state.attempt, config.initial_delay_ms
            )
            state.total_delay_ms += delay_ms

            # Call on_retry callback if provided
            if config.on_retry:
                config.on_retry(
                    attempt=state.attempt,
                    max_attempts=config.max_attempts,
                    delay_ms=delay_ms,
                    error=e
                )

            # Wait before next attempt
            await asyncio.sleep(delay_ms / 1000)

    raise last_error


def format_retry_config(config: RetryConfig) -> str:
    """Format retry configuration as human-readable string."""
    lines = []
    lines.append(f"Retry Configuration:")
    lines.append(f"  Max Attempts: {config.max_attempts}")
    lines.append(f"  Initial Delay: {config.initial_delay_ms}ms")
    lines.append(f"  Max Delay: {config.max_delay_ms}ms")
    lines.append(f"  Backoff Strategy: {config.backoff.value}")

    if config.retryable_errors:
        lines.append(f"  Retryable Errors: {', '.join(config.retryable_errors)}")

    if config.fatal_errors:
        lines.append(f"  Fatal Errors: {', '.join(config.fatal_errors)}")

    return "\n".join(lines)
