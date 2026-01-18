import asyncio
import time
from typing import Dict, List


class TPMLimiter:
    """
    Simple Sliding Window Rate Limiter for Tokens Per Minute (TPM).
    Supports Priority: High priority (user) jumps the line.
    """

    def __init__(self, limit: int = 10000):
        self.limit = limit
        self.window_size = 60  # 1 minute
        self.usage_history: List[tuple[float, int]] = []
        self.lock = asyncio.Lock()
        self.hp_waiters = 0  # Count of high-priority requests waiting

    async def _clean_history(self):
        now = time.time()
        self.usage_history = [
            (t, u) for t, u in self.usage_history if now - t < self.window_size
        ]

    async def get_current_usage(self) -> int:
        await self._clean_history()
        return sum(u for t, u in self.usage_history)

    async def wait_for_capacity(self, estimated_tokens: int, priority: str = "high"):
        """
        Wait until there is enough capacity.
        High priority requests jump ahead of low priority ones.
        """
        is_hp = priority == "high"

        if is_hp:
            self.hp_waiters += 1

        try:
            while True:
                async with self.lock:
                    current_usage = await self.get_current_usage()

                    # Capacity check
                    has_tokens = current_usage + estimated_tokens <= self.limit

                    # Priority logic:
                    # If I am low priority, I MUST wait if any high priority task is waiting,
                    # UNLESS the window is very empty (e.g. < 20% usage) to avoid total starvation.
                    can_proceed = False
                    if is_hp:
                        if has_tokens:
                            can_proceed = True
                    else:
                        if has_tokens and (
                            self.hp_waiters == 0 or current_usage < (self.limit * 0.2)
                        ):
                            can_proceed = True

                    if can_proceed:
                        self.usage_history.append((time.time(), estimated_tokens))
                        if is_hp:
                            self.hp_waiters -= 1
                        return

                    wait_time = 2 if is_hp else 5
                    if not is_hp and self.hp_waiters > 0:
                        print(
                            f"💤 [RATE_LIMIT] Low-priority task backing off because User (HP) is waiting..."
                        )

                await asyncio.sleep(wait_time)
        except Exception as e:
            if is_hp:
                self.hp_waiters = max(0, self.hp_waiters - 1)
            raise e

    def estimate_tokens(self, text: str) -> int:
        """Rough estimation: 1 token ~= 4 characters."""
        return len(text) // 4 + 20  # adding some buffer


# Global instance
tpm_limiter = TPMLimiter()
