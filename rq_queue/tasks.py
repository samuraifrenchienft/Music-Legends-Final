# queue/tasks.py
import logging
from rq import get_current_job
import redis
import os
from rq_queue.locks import user_lock, trade_lock, card_lock
from database import DatabaseManager
from card_economy import CardEconomyManager
from drop_system import DropSystem
from uuid import uuid4
from rq_queue.redis_connection import QUEUES

# Initialize services
db = DatabaseManager()
economy = CardEconomyManager(db)

def task_open_pack(user_id, pack_type, genre=None, job_id=None):
    """Open pack with idempotent locking"""
    job_id = job_id or str(uuid4())
    
    with user_lock(user_id):
        # Check if it's a Founder Pack
        from packs.founder_packs_v2 import founder_packs_v2
        
        is_founder_pack = pack_type in [founder_packs_v2.PACK_BLACK, founder_packs_v2.PACK_SILVER]
        
        if is_founder_pack:
            # Use new Founder Pack implementation
            try:
                cards = founder_packs_v2.open_pack(user_id, pack_type, genre)
                
                result = {
                    'success': True, 
                    'cards': cards, 
                    'pack_type': pack_type,
                    'job_id': job_id,
                    'is_founder_pack': True
                }
                
                logging.info(f"Founder Pack opened successfully: {pack_type} for user {user_id}")
                return result
                
            except Exception as e:
                logging.error(f"Failed to open Founder Pack: {e}")
                return {'success': False, 'error': f'Founder Pack error: {str(e)}', 'job_id': job_id}
        
        else:
            # Regular pack logic
            from card_economy import economy_manager
            
            try:
                cards = economy_manager._generate_pack_cards(pack_type)
                
                # Award cards to user
                awarded_cards = []
                for card in cards:
                    economy_manager._award_card_to_user(user_id, card)
                    awarded_cards.append(card)
                
                result = {
                    'success': True, 
                    'cards': awarded_cards, 
                    'pack_type': pack_type,
                    'job_id': job_id
                }
                
                return result
                
            except Exception as e:
                logging.error(f"Failed to open regular pack: {e}")
                return {'success': False, 'error': f'Pack error: {str(e)}', 'job_id': job_id}

def task_finalize_trade(trade_id: str):
    """Finalize trade with atomic locking"""
    job = get_current_job()
    job_id = job.id if job else 'unknown'
    
    logging.info(f"Finalizing trade {trade_id}, job {job_id}")
    
    with trade_lock(trade_id):
        # Check if duplicate
        if _is_duplicate_job('finalize_trade', trade_id):
            logging.warning(f"Duplicate trade finalization detected for trade {trade_id}")
            return {'success': False, 'error': 'Duplicate trade finalization', 'job_id': job_id}
        
        # Get trade data from database
        # This would need to be implemented based on your trade system
        trade_data = _get_trade_data(trade_id)
        
        if not trade_data:
            return {'success': False, 'error': 'Trade not found', 'job_id': job_id}
        
        # Process trade finalization
        try:
            # Transfer cards between users
            result = _process_trade_transfer(trade_data)
            
            # Update trade status
            _update_trade_status(trade_id, 'completed')
            
            return {
                'success': True,
                'trade_id': trade_id,
                'result': result,
                'job_id': job_id
            }
        except Exception as e:
            logging.error(f"Error finalizing trade {trade_id}: {e}")
            return {'success': False, 'error': str(e), 'job_id': job_id}

async def task_resolve_drop(drop_id: str, user_id: int, reaction_number: int):
    """Resolve drop claim with locking"""
    job = get_current_job()
    job_id = job.id if job else 'unknown'
    
    logging.info(f"Resolving drop {drop_id} for user {user_id}, reaction {reaction_number}, job {job_id}")
    
    # Use drop system for resolution
    from drop_system import drop_system
    
    if not drop_system:
        return {'success': False, 'error': 'Drop system not available', 'job_id': job_id}
    
    # Check for duplicate resolution
    if _is_duplicate_job('resolve_drop', drop_id, user_id, reaction_number):
        logging.warning(f"Duplicate drop resolution detected for drop {drop_id}")
        return {'success': False, 'error': 'Duplicate drop resolution', 'job_id': job_id}
    
    try:
        result = drop_system.resolve_drop(None, user_id, reaction_number)
        return {
            'success': result.get('success', False),
            'card': result.get('card'),
            'error': result.get('error'),
            'job_id': job_id
        }
    except Exception as e:
        logging.error(f"Error resolving drop {drop_id}: {e}")
        return {'success': False, 'error': str(e), 'job_id': job_id}

def task_burn(card_id: str, user_id: int):
    """Burn card for dust with user locking"""
    job = get_current_job()
    job_id = job.id if job else 'unknown'
    
    logging.info(f"Burning card {card_id} for user {user_id}, job {job_id}")
    
    with user_lock(user_id):
        # Check for duplicate burn
        if _is_duplicate_job('burn', card_id, user_id):
            logging.warning(f"Duplicate card burn detected for card {card_id}")
            return {'success': False, 'error': 'Duplicate card burn', 'job_id': job_id}
        
        try:
            result = economy.burn_card_for_dust(user_id, card_id)
            return {
                'success': result.get('success', False),
                'dust_earned': result.get('dust_earned', 0),
                'error': result.get('error'),
                'job_id': job_id
            }
        except Exception as e:
            logging.error(f"Error burning card {card_id}: {e}")
            return {'success': False, 'error': str(e), 'job_id': job_id}

def task_increment_cap(artist_name: str, tier: str):
    """Increment card cap with locking"""
    job = get_current_job()
    job_id = job.id if job else 'unknown'
    
    logging.info(f"Incrementing cap for {artist_name} {tier}, job {job_id}")
    
    # Use artist-tier specific lock
    lock_key = f"cap:{artist_name}:{tier}"
    from .locks import RedisLock
    
    with RedisLock(lock_key, ttl=5):
        # Check for duplicate increment
        if _is_duplicate_job('increment_cap', artist_name, tier):
            logging.warning(f"Duplicate cap increment detected for {artist_name} {tier}")
            return {'success': False, 'error': 'Duplicate cap increment', 'job_id': job_id}
        
        try:
            # Increment cap in database
            _increment_card_cap(artist_name, tier)
            
            return {
                'success': True,
                'artist_name': artist_name,
                'tier': tier,
                'job_id': job_id
            }
        except Exception as e:
            logging.error(f"Error incrementing cap for {artist_name} {tier}: {e}")
            return {'success': False, 'error': str(e), 'job_id': job_id}

# Helper functions
def _is_duplicate_job(action: str, *args) -> bool:
    """Check if this is a duplicate job"""
    job = get_current_job()
    if not job:
        return False
    
    # Create job signature
    job_signature = f"{action}:{args}"
    
    # Check in Redis if this job was recently processed
    key = f"job_cache:{job_signature}"
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    redis_conn = redis.from_url(redis_url, decode_responses=True)
    recent_job = redis_conn.get(key)
    
    if recent_job:
        return True
    
    # Mark this job as processed (with TTL of 5 minutes)
    redis_conn.setex(key, 300, job.id)
    return False

def _get_trade_data(trade_id: str) -> dict:
    """Get trade data from database"""
    # This would need to be implemented based on your trade system
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        result = cursor.fetchone()
        
        if result:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
    
    return None

def _process_trade_transfer(trade_data: dict) -> dict:
    """Process card transfer between users"""
    # This would implement the actual trade logic
    # Transfer cards from initiator to receiver
    # Update ownership in database
    # Record trade completion
    
    return {'success': True, 'transferred': len(trade_data.get('cards', []))}

def _update_trade_status(trade_id: str, status: str):
    """Update trade status in database"""
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE trades SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE trade_id = ?",
            (status, trade_id)
        )
        conn.commit()

def _increment_card_cap(artist_name: str, tier: str):
    """Increment card cap in database"""
    # This would update your season card caps
    from season_system import season_manager
    
    if season_manager:
        season_manager.increment_card_print(artist_name, tier)
