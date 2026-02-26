# queue.py
import asyncio
from typing import Dict, Any, Callable, TypeVar, Generic
from dataclasses import dataclass

T = TypeVar('T')

@dataclass
class Task(Generic[T]):
    key: str
    action: Callable[[], T]

class ActionQueue:
    def __init__(self):
        self.locks: Dict[str, asyncio.Lock] = {}
        self._loop = asyncio.get_event_loop()
    
    async def run(self, task: Task[T]) -> T:
        """Run a task with locking mechanism"""
        # Get or create lock for this key
        if task.key not in self.locks:
            self.locks[task.key] = asyncio.Lock()
        
        lock = self.locks[task.key]
        
        # Wait for lock to be available
        async with lock:
            return await task.action()
    
    async def run_with_timeout(self, task: Task[T], timeout: float = 30.0) -> T:
        """Run a task with timeout"""
        try:
            return await asyncio.wait_for(self.run(task), timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task {task.key} timed out after {timeout} seconds")
    
    def is_locked(self, key: str) -> bool:
        """Check if a key is currently locked"""
        if key not in self.locks:
            return False
        return self.locks[key].locked()
    
    def get_lock_status(self) -> Dict[str, bool]:
        """Get status of all locks"""
        return {key: lock.locked() for key, lock in self.locks.items()}
    
    def clear_lock(self, key: str):
        """Clear a specific lock (use with caution)"""
        if key in self.locks:
            del self.locks[key]

# Global queue instance
action_queue = ActionQueue()

# Example usage:
# 
# async def example_usage():
#     # Define tasks
#     task1 = Task(key="user_123", action=lambda: process_user_data(123))
#     task2 = Task(key="user_123", action=lambda: process_user_data(456))  # Will wait
#     task3 = Task(key="user_456", action=lambda: process_user_data(789))  # Can run concurrently
#     
#     # Run tasks
#     result1 = await action_queue.run(task1)
#     result2 = await action_queue.run(task2)  # Waits for task1 to complete
#     result3 = await action_queue.run(task3)  # Can run while task2 waits
#     
#     return result1, result2, result3
