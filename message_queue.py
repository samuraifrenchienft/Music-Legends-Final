# message_queue.py
import os
import redis
import json
import asyncio
import uuid
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

@dataclass
class QueueMessage:
    id: str
    queue: str
    payload: Dict[str, Any]
    attempts: int = 0
    max_attempts: int = 3
    created_at: float = None
    next_attempt_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().timestamp()
        if self.next_attempt_at is None:
            self.next_attempt_at = self.created_at

class RedisMessageQueue:
    def __init__(self, redis_url: str = None):
        if redis_url is None:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.queues = {
            'drop-queue': self._handle_drop,
            'pack-queue': self._handle_pack,
            'trade-queue': self._handle_trade,
            'burn-queue': self._handle_burn,
            'event-queue': self._handle_event
        }
        self.dead_letter_queue = 'dlq'
        self.processing = set()  # Track currently processing message IDs
        self.processing_timestamps: Dict[str, float] = {}  # Track when messages started processing
        
    async def enqueue(self, queue_name: str, payload: Dict[str, Any], delay_ms: int = 0) -> str:
        """Enqueue a message with optional delay"""
        message = QueueMessage(
            id=str(uuid.uuid4()),
            queue=queue_name,
            payload=payload,
            next_attempt_at=datetime.now().timestamp() + (delay_ms / 1000)
        )
        
        # Store message
        self._store_message(message)
        
        # Add to queue
        score = message.next_attempt_at
        self.redis.zadd(f"queue:{queue_name}", {message.id: score})
        
        logging.info(f"Enqueued message {message.id} to {queue_name}")
        return message.id
    
    async def dequeue(self, queue_name: str) -> Optional[QueueMessage]:
        """Dequeue next available message"""
        # Clean up stale processing entries (older than 5 minutes)
        now_time = time.time()
        stale_ids = [mid for mid, timestamp in self.processing_timestamps.items()
                     if now_time - timestamp > 300]
        for stale_id in stale_ids:
            self.processing.discard(stale_id)
            self.processing_timestamps.pop(stale_id, None)

        # Get next message by score (earliest)
        now = datetime.now().timestamp()
        result = self.redis.zrangebyscore(f"queue:{queue_name}", 0, now, start=0, num=1)

        if not result:
            return None

        message_id = result[0]

        # Check if already being processed
        if message_id in self.processing:
            return None

        # Mark as processing
        self.processing.add(message_id)
        self.processing_timestamps[message_id] = now_time
        
        # Get message data
        message_data = self.redis.hgetall(f"msg:{message_id}")
        if not message_data:
            self.processing.discard(message_id)
            return None
        
        # Remove from queue
        self.redis.zrem(f"queue:{queue_name}", message_id)
        
        message = QueueMessage(
            id=message_id,
            queue=message_data['queue'],
            payload=json.loads(message_data['payload']),
            attempts=int(message_data['attempts']),
            max_attempts=int(message_data['max_attempts']),
            created_at=float(message_data['created_at']),
            next_attempt_at=float(message_data['next_attempt_at'])
        )
        
        logging.info(f"Dequeued message {message.id} from {queue_name}")
        return message
    
    async def complete(self, message: QueueMessage):
        """Mark message as completed"""
        # Remove from processing
        self.processing.discard(message.id)
        self.processing_timestamps.pop(message.id, None)

        # Delete message data
        self.redis.delete(f"msg:{message.id}")

        logging.info(f"Completed message {message.id}")
    
    async def retry(self, message: QueueMessage, error: str = None):
        """Retry a failed message"""
        message.attempts += 1
        
        if message.attempts >= message.max_attempts:
            # Send to dead letter queue
            await self._send_to_dlq(message, error)
            await self.complete(message)
        else:
            # Schedule retry with exponential backoff
            backoff_seconds = 2 ** message.attempts
            message.next_attempt_at = datetime.now().timestamp() + backoff_seconds
            
            # Update message
            self._store_message(message)
            
            # Re-add to queue
            self.redis.zadd(f"queue:{message.queue}", {message.id: message.next_attempt_at})
            
            logging.info(f"Retrying message {message.id} (attempt {message.attempts})")

        # Remove from processing
        self.processing.discard(message.id)
        self.processing_timestamps.pop(message.id, None)
    
    def _store_message(self, message: QueueMessage):
        """Store message data"""
        data = {
            'id': message.id,
            'queue': message.queue,
            'payload': json.dumps(message.payload),
            'attempts': message.attempts,
            'max_attempts': message.max_attempts,
            'created_at': message.created_at,
            'next_attempt_at': message.next_attempt_at
        }
        self.redis.hset(f"msg:{message.id}", mapping=data)
    
    async def _send_to_dlq(self, message: QueueMessage, error: str = None):
        """Send message to dead letter queue"""
        dlq_data = {
            'original_message': asdict(message),
            'error': error,
            'failed_at': datetime.now().isoformat()
        }
        self.redis.lpush(self.dead_letter_queue, json.dumps(dlq_data))
        logging.error(f"Sent message {message.id} to DLQ: {error}")
    
    async def _handle_drop(self, payload: Dict[str, Any]):
        """Handle drop queue message"""
        # Import here to avoid circular imports
        from drop_system import drop_system
        
        channel_id = payload['channel_id']
        user_id = payload['user_id']
        reaction_number = payload['reaction_number']
        
        result = await drop_system.resolve_drop(channel_id, user_id, reaction_number)
        return result
    
    async def _handle_pack(self, payload: Dict[str, Any]):
        """Handle pack queue message"""
        from card_economy import economy_manager
        
        user_id = payload['user_id']
        pack_type = payload['pack_type']
        quantity = payload.get('quantity', 1)
        
        cards = []
        for _ in range(quantity):
            card_data = economy_manager._generate_pack_cards(pack_type)
            cards.extend(card_data)
        
        # Award cards to user
        for card in cards:
            economy_manager._award_card_to_user(user_id, card)
        
        return {'success': True, 'cards': cards}
    
    async def _handle_trade(self, payload: Dict[str, Any]):
        """Handle trade queue message"""
        trade_id = payload['trade_id']
        action = payload['action']  # 'finalize', 'cancel'
        
        # Implement trade logic here
        if action == 'finalize':
            # Finalize trade
            pass
        elif action == 'cancel':
            # Cancel trade
            pass
        
        return {'trade_id': trade_id, 'action': action}
    
    async def _handle_burn(self, payload: Dict[str, Any]):
        """Handle burn queue message"""
        from card_economy import economy_manager
        
        user_id = payload['user_id']
        card_id = payload['card_id']
        
        result = economy_manager.burn_card_for_dust(user_id, card_id)
        return result
    
    async def _handle_event(self, payload: Dict[str, Any]):
        """Handle event queue message"""
        event_type = payload['type']
        data = payload['data']
        
        # Log analytics, track metrics, etc.
        logging.info(f"Event: {event_type} - {data}")
        
        return {'event_type': event_type, 'logged': True}
    
    async def process_queue(self, queue_name: str):
        """Process messages from a specific queue"""
        while True:
            try:
                message = await self.dequeue(queue_name)
                if not message:
                    await asyncio.sleep(1)  # No messages, wait
                    continue
                
                # Get handler
                handler = self.queues.get(message.queue)
                if not handler:
                    await self.retry(message, f"No handler for queue {message.queue}")
                    continue
                
                # Process message
                try:
                    result = await handler(message.payload)
                    await self.complete(message)
                    
                    # Log success
                    logging.info(f"Processed {message.queue} message {message.id}")
                    
                except Exception as e:
                    await self.retry(message, str(e))
                    
            except Exception as e:
                logging.error(f"Error processing queue {queue_name}: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = {}
        
        for queue_name in self.queues.keys():
            # Queue length
            length = await self.redis.zcard(f"queue:{queue_name}")
            
            # Processing count
            processing = len([mid for mid in self.processing if mid.startswith(queue_name)])
            
            stats[queue_name] = {
                'length': length,
                'processing': processing
            }
        
        # DLQ length
        stats['dead_letter_queue'] = await self.redis.llen(self.dead_letter_queue)
        
        return stats

# Global queue instance
message_queue = None

def initialize_message_queue(redis_url: str = None):
    """Initialize the message queue"""
    global message_queue
    if redis_url is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    message_queue = RedisMessageQueue(redis_url)
    return message_queue
