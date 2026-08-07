import time
import asyncio

class TokenBucket:
    """
    Token Bucket algorithm for bandwidth rate limiting (Throttling).
    Each client should have its own instance to prevent cross-client interference.
    """
    def __init__(self, rate_kbps: float):
        # Rate calculated in bytes per second
        self.rate_bps = rate_kbps * 1024
        self.capacity = self.rate_bps
        self.tokens = self.capacity
        self.last_update = time.monotonic()

    async def consume(self, num_bytes: int):
        """Consume tokens corresponding to the number of bytes to transmit."""
        if self.rate_bps <= 0:
            return  # No rate limit
            
        while num_bytes > 0:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Refill tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate_bps)
            
            if self.tokens >= num_bytes:
                self.tokens -= num_bytes
                num_bytes = 0
            else:
                # Consume all currently available tokens
                num_bytes -= self.tokens
                self.tokens = 0
                
                # Calculate sleep duration needed to accumulate enough tokens for the remainder
                # Yield CPU execution to other tasks by sleeping in small intervals
                sleep_time = num_bytes / self.rate_bps
                await asyncio.sleep(min(sleep_time, 0.1))