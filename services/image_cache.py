# services/image_cache.py
"""
Image Cache Service
Handles image URL safety and caching for performance
"""

import time
import hashlib
from typing import Optional, Dict, Any
from pathlib import Path

# Default image for missing/inappropriate images
DEFAULT_IMG = "https://via.placeholder.com/300x300/cccccc/000000?text=No+Image"

# Cache directory
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Cache settings
CACHE_DURATION = 3600  # 1 hour
MAX_CACHE_SIZE = 1000  # Maximum number of cached URLs

class ImageCache:
    """Simple in-memory cache for image URLs"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = MAX_CACHE_SIZE
    
    def get(self, url: str) -> Optional[Dict[str, Any]]:
        """Get cached image data"""
        try:
            if url in self.cache:
                cached = self.cache[url]
                
                # Check if expired
                if time.time() - cached['timestamp'] < CACHE_DURATION:
                    return cached
                else:
                    # Remove expired entry
                    del self.cache[url]
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting cached image: {e}")
            return None
    
    def set(self, url: str, safe: bool, reason: str = ""):
        """Set cached image data"""
        try:
            # Remove oldest entries if cache is full
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]['timestamp'])
                del self.cache[oldest_key]
            
            self.cache[url] = {
                'safe': safe,
                'reason': reason,
                'timestamp': time.time()
            }
            
        except Exception as e:
            print(f"❌ Error setting cached image: {e}")
    
    def clear(self):
        """Clear all cached data"""
        try:
            self.cache.clear()
        except Exception as e:
            print(f"❌ Error clearing cache: {e}")
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)


# Global cache instance
image_cache = ImageCache()


def safe_image(url: Optional[str]) -> str:
    """
    Check if image URL is safe and return safe URL or default
    
    Args:
        url: Image URL to check
        
    Returns:
        Safe image URL or default image
    """
    if not url:
        return DEFAULT_IMG
    
    # Check cache first
    cached = image_cache.get(url)
    if cached:
        return url if cached['safe'] else DEFAULT_IMG
    
    # Perform safety check
    safe, reason = check_image_safety(url)
    
    # Cache the result
    image_cache.set(url, safe, reason)
    
    return url if safe else DEFAULT_IMG


def check_image_safety(url: str) -> tuple[bool, str]:
    """
    Check if image URL is safe
    
    Args:
        url: Image URL to check
        
    Returns:
        (is_safe, reason) tuple
    """
    try:
        # Basic URL validation
        if not url or not isinstance(url, str):
            return False, "Invalid URL"
        
        # Check if URL starts with http/https
        if not url.startswith(('http://', 'https://')):
            return False, "Invalid protocol"
        
        # Check for suspicious domains
        suspicious_domains = [
            'nsfw', 'adult', 'xxx', 'porn', 'sex', 'nude',
            'explicit', 'erotic', 'mature', '18+', 'xxx',
            'hentai', 'rule34', 'pornhub', 'xvideos',
            'youporn', 'redtube', 'tube8', 'spankbang'
        ]
        
        url_lower = url.lower()
        for domain in suspicious_domains:
            if domain in url_lower:
                return False, f"Suspicious domain: {domain}"
        
        # Check for suspicious file patterns
        suspicious_patterns = [
            'xxx', 'sex', 'nude', 'porn', 'adult',
            'explicit', 'erotic', 'mature', '18+',
            'nsfw', 'hentai', 'rule34'
        ]
        
        for pattern in suspicious_patterns:
            if pattern in url_lower:
                return False, f"Suspicious pattern: {pattern}"
        
        # Check for common image file extensions
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        has_valid_extension = any(url_lower.endswith(ext) for ext in valid_extensions)
        
        # Allow YouTube thumbnails (they don't have extensions)
        youtube_domains = ['i.ytimg.com', 'yt3.ggpht.com', 'img.youtube.com']
        is_youtube = any(domain in url for domain in youtube_domains)
        
        if not has_valid_extension and not is_youtube:
            return False, "Invalid image format"
        
        # Check for very large URLs (might be suspicious)
        if len(url) > 500:
            return False, "URL too long"
        
        # Check for encoded content that might be suspicious
        if '%3A' in url or '%2F' in url:
            # URL encoded, check if it contains suspicious content
            decoded = url.replace('%3A', ':').replace('%2F', '/')
            for pattern in suspicious_patterns:
                if pattern in decoded.lower():
                    return False, f"Suspicious encoded content: {pattern}"
        
        # Check for base64 encoded images
        if 'base64' in url_lower or 'image/' in url_lower:
            return False, "Base64 encoded image"
        
        # Check for data URLs
        if url.startswith('data:'):
            return False, "Data URL not allowed"
        
        # Check for localhost/private IPs
        if 'localhost' in url_lower or '127.0.0.1' in url_lower:
            return False, "Localhost not allowed"
        
        # Check for private IP ranges
        private_ranges = ['192.168.', '10.', '172.16.', '169.254.']
        for private_range in private_ranges:
            if private_range in url:
                return False, f"Private IP range: {private_range}"
        
        return True, "Safe"
        
    except Exception as e:
        print(f"❌ Error checking image safety: {e}")
        return False, f"Error: {e}"


def get_image_info(url: str) -> Dict[str, Any]:
    """
    Get detailed information about an image URL
    
    Args:
        url: Image URL
        
    Returns:
        Dictionary with image information
    """
    try:
        # Check cache first
        cached = image_cache.get(url)
        if cached:
            return {
                'url': url,
                'safe': cached['safe'],
                'reason': cached['reason'],
                'cached': True,
                'cached_at': cached['timestamp']
            }
        
        # Perform safety check
        safe, reason = check_image_safety(url)
        
        # Cache the result
        image_cache.set(url, safe, reason)
        
        return {
            'url': url,
            'safe': safe,
            'reason': reason,
            'cached': False,
            'cached_at': None
        }
        
    except Exception as e:
        print(f"❌ Error getting image info: {e}")
        return {
            'url': url,
            'safe': False,
            'reason': f"Error: {e}",
            'cached': False,
            'cached_at': None
        }


def batch_check_images(urls: list[str]) -> Dict[str, Dict[str, Any]]:
    """
    Check multiple image URLs for safety
    
    Args:
        urls: List of image URLs to check
        
    Returns:
        Dictionary mapping URLs to image info
    """
    results = {}
    
    for url in urls:
        if url:
            results[url] = get_image_info(url)
    
    return results


def cleanup_cache():
    """Clean up expired cache entries"""
    try:
        current_time = time.time()
        expired_keys = []
        
        for key, value in image_cache.cache.items():
            if current_time - value['timestamp'] >= CACHE_DURATION:
                expired_keys.append(key)
        
        for key in expired_keys:
            del image_cache.cache[key]
        
        if expired_keys:
            print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
            
    except Exception as e:
        print(f"❌ Error cleaning up cache: {e}")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics
    
    Returns:
        Dictionary with cache statistics
    """
    try:
        total_entries = len(image_cache.cache)
        safe_entries = sum(1 for v in image_cache.cache.values() if v['safe'])
        unsafe_entries = total_entries - safe_entries
        
        # Calculate cache age statistics
        current_time = time.time()
        ages = [current_time - v['timestamp'] for v in image_cache.cache.values()]
        
        if ages:
            avg_age = sum(ages) / len(ages)
            oldest_age = max(ages)
            newest_age = min(ages)
        else:
            avg_age = 0
            oldest_age = 0
            newest_age = 0
        
        return {
            'total_entries': total_entries,
            'safe_entries': safe_entries,
            'unsafe_entries': unsafe_entries,
            'safe_percentage': f"{(safe_entries / total_entries * 100):.1f}%" if total_entries > 0 else "0%",
            'avg_age_seconds': round(avg_age, 1),
            'oldest_age_seconds': round(oldest_age, 1),
            'newest_age_seconds': round(newest_age, 1),
            'max_size': image_cache.max_size,
            'cache_duration': CACHE_DURATION
        }
        
    except Exception as e:
        print(f"❌ Error getting cache stats: {e}")
        return {
            'total_entries': 0,
            'safe_entries': 0,
            'unsafe_entries': 0,
            'safe_percentage': "0%",
            'avg_age_seconds': 0,
            'oldest_age_seconds': 0,
            'newest_age_seconds': 0,
            'max_size': image_cache.max_size,
            'cache_duration': CACHE_DURATION
        }


def preload_images(urls: list[str]) -> Dict[str, bool]:
    """
    Preload multiple images into cache
    
    Args:
        urls: List of image URLs to preload
        
    Returns:
        Dictionary mapping URLs to preload success status
    """
    results = {}
    
    for url in urls:
        if url:
            try:
                # Check if already cached
                cached = image_cache.get(url)
                if cached:
                    results[url] = True
                else:
                    # Perform safety check and cache
                    safe, reason = check_image_safety(url)
                    image_cache.set(url, safe, reason)
                    results[url] = safe
            except Exception as e:
                print(f"❌ Error preloading image {url}: {e}")
                results[url] = False
    
    return results


# Example usage
def example_usage():
    """Example of image cache usage"""
    
    print("🖼️ Image Cache Examples:")
    print("========================")
    
    # Test safe image
    safe_url = "https://i.ytimg.com/vi/queen/maxresdefault.jpg"
    print(f"\n1. Testing safe image: {safe_url}")
    
    safe_result = safe_image(safe_url)
    print(f"   Result: {safe_result}")
    
    # Test unsafe image
    unsafe_url = "https://nsfw-site.com/image.jpg"
    print(f"\n2. Testing unsafe image: {unsafe_url}")
    
    unsafe_result = safe_image(unsafe_url)
    print(f"   Result: {unsafe_result}")
    
    # Test invalid URL
    print(f"\n3. Testing invalid URL: {None}")
    
    invalid_result = safe_image(None)
    print(f"   Result: {invalid_result}")
    
    # Get image info
    print(f"\n4. Getting image info for: {safe_url}")
    info = get_image_info(safe_url)
    print(f"   Safe: {info['safe']}")
    print(f"   Reason: {info['reason']}")
    print(f"   Cached: {info['cached']}")
    
    # Get cache stats
    print(f"\n5. Cache statistics:")
    stats = get_cache_stats()
    print(f"   Total entries: {stats['total_entries']}")
    print(f"   Safe entries: {stats['safe_entries']}")
    print(f"   Safe percentage: {stats['safe_percentage']}")
    print(f"   Max size: {stats['max_size']}")
    
    # Batch check
    urls = [safe_url, unsafe_url, "https://example.com/image.png"]
    print(f"\n6. Batch checking {len(urls)} URLs:")
    batch_results = batch_check_images(urls)
    for url, result in batch_results.items():
        print(f"   {url}: {'✅' if result['safe'] else '❌'} {result['reason']}")


if __name__ == "__main__":
    example_usage()
