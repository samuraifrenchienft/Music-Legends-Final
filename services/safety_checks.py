# services/safety_checks.py
"""
Enhanced Safety Check Service
Comprehensive validation for creator pack previews
"""

from typing import Dict, List, Tuple, Any
import re
from urllib.parse import urlparse
from services.creator_moderation import creator_moderation

class SafetyCheckService:
    """Service for comprehensive safety checks"""
    
    def __init__(self):
        self.moderation = creator_moderation
        
        # Suspicious domains and patterns
        self.suspicious_domains = [
            "nsfw", "adult", "xxx", "porn", "hentai",
            "explicit", "mature", "18+", "r18",
            "suspicious", "malware", "virus", "phishing"
        ]
        
        self.inappropriate_keywords = [
            "nsfw", "porn", "xxx", "adult", "explicit",
            "hate", "racist", "nazi", "terrorist",
            "illegal", "crime", "violence", "weapon",
            "drug", "suicide", "self-harm"
        ]
        
        self.impersonation_patterns = [
            r"official", r"vevo", r"topic", r"auto",
            r"channel", r"music", r"records", r"studio",
            r"entertainment", r"productions", r"reupload"
        ]
    
    def safe_images(self, preview: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Comprehensive image safety check
        
        Args:
            preview: Preview data dictionary
            
        Returns:
            (is_safe, message) tuple
        """
        try:
            artists = preview.get("artists", [])
            if not artists:
                return False, "No artists found in preview"
            
            issues = []
            
            for artist in artists:
                artist_name = artist.get("name", "Unknown Artist")
                image_url = artist.get("image", "")
                
                # Check 1: Image exists
                if not image_url:
                    issues.append(f"No image for {artist_name}")
                    continue
                
                # Check 2: Valid URL format
                if not self._is_valid_url(image_url):
                    issues.append(f"Invalid image URL for {artist_name}")
                    continue
                
                # Check 3: Safe domain
                if not self._is_safe_domain(image_url):
                    issues.append(f"Unsafe image domain for {artist_name}")
                
                # Check 4: Safe file extension
                if not self._is_safe_file_extension(image_url):
                    issues.append(f"Unsafe file extension for {artist_name}")
                
                # Check 5: No suspicious patterns in URL
                if self._has_suspicious_patterns(image_url):
                    issues.append(f"Suspicious URL patterns for {artist_name}")
                
                # Check 6: Reasonable file size (if detectable)
                if not self._is_reasonable_image_size(image_url):
                    issues.append(f"Unreasonable image size for {artist_name}")
            
            if issues:
                return False, "; ".join(issues)
            
            return True, "All images safe and appropriate"
            
        except Exception as e:
            return False, f"Error checking images: {e}"
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    def _is_safe_domain(self, url: str) -> bool:
        """Check if domain is safe"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Check against suspicious domains
            for suspicious in self.suspicious_domains:
                if suspicious in domain:
                    return False
            
            # Allow common image domains
            safe_domains = [
                "youtube.com", "img.youtube.com", "i.ytimg.com",
                "discord.com", "cdn.discordapp.com",
                "googleusercontent.com", "ggpht.com",
                "instagram.com", "cdn.instagram.com",
                "twitter.com", "pbs.twimg.com",
                "facebook.com", "scontent.xx.fbcdn.net"
            ]
            
            return any(safe in domain for safe in safe_domains)
            
        except Exception:
            return False
    
    def _is_safe_file_extension(self, url: str) -> bool:
        """Check if file extension is safe"""
        safe_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]
        
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            return any(path.endswith(ext) for ext in safe_extensions)
        except Exception:
            return False
    
    def _has_suspicious_patterns(self, url: str) -> bool:
        """Check for suspicious patterns in URL"""
        url_lower = url.lower()
        
        # Check for suspicious keywords
        for keyword in self.inappropriate_keywords:
            if keyword in url_lower:
                return True
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r"\.exe$", r"\.bat$", r"\.cmd$", r"\.scr$",
            r"\.zip$", r"\.rar$", r"\.tar$", r"\.gz$",
            r"download", r"torrent", r"pirate", r"illegal"
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, url_lower):
                return True
        
        return False
    
    def _is_reasonable_image_size(self, url: str) -> bool:
        """
        Check if image size is reasonable
        Note: This is a basic check - in production you'd want to actually download and check
        """
        try:
            # For now, just check URL length as a basic proxy
            # Very long URLs might indicate suspicious content
            return len(url) < 500
        except Exception:
            return True  # Assume safe if we can't check
    
    def verify_artists_real(self, preview: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verify artists appear to be real
        
        Args:
            preview: Preview data dictionary
            
        Returns:
            (are_real, message) tuple
        """
        try:
            artists = preview.get("artists", [])
            if not artists:
                return False, "No artists found"
            
            fake_indicators = []
            
            for artist in artists:
                artist_name = artist.get("name", "")
                
                # Check 1: Name has reasonable length
                if len(artist_name) < 2 or len(artist_name) > 100:
                    fake_indicators.append(f"Unusual name length for {artist_name}")
                
                # Check 2: Name doesn't contain suspicious patterns
                if self._has_fake_name_patterns(artist_name):
                    fake_indicators.append(f"Suspicious name patterns for {artist_name}")
                
                # Check 3: Has some YouTube data (if channel_id exists)
                if not artist.get("channel_id") and not artist.get("subscribers", 0) > 0:
                    fake_indicators.append(f"No YouTube data for {artist_name}")
                
                # Check 4: Reasonable subscriber count
                subscribers = artist.get("subscribers", 0)
                if subscribers > 0 and (subscribers < 10 or subscribers > 500000000):
                    fake_indicators.append(f"Unusual subscriber count for {artist_name}")
                
                # Check 5: Reasonable view count
                views = artist.get("views", 0)
                if views > 0 and (views < 100 or views > 10000000000):
                    fake_indicators.append(f"Unusual view count for {artist_name}")
            
            if fake_indicators:
                return False, "; ".join(fake_indicators)
            
            return True, "All artists appear to be real"
            
        except Exception as e:
            return False, f"Error verifying artists: {e}"
    
    def _has_fake_name_patterns(self, name: str) -> bool:
        """Check for fake name patterns"""
        name_lower = name.lower()
        
        # Check for random characters
        if re.search(r"[0-9]{3,}", name_lower):
            return True
        
        # Check for spam patterns
        if re.search(r"(.)\1{4,}", name_lower):  # 5+ repeated characters
            return True
        
        # Check for common fake patterns
        fake_patterns = [
            r"test", r"demo", r"example", r"sample",
            r"fake", r"bot", r"auto", r"generated"
        ]
        
        for pattern in fake_patterns:
            if pattern in name_lower:
                return True
        
        return False
    
    def verify_no_impersonation(self, preview: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verify no impersonation attempts
        
        Args:
            preview: Preview data dictionary
            
        Returns:
            (no_impersonation, message) tuple
        """
        try:
            artists = preview.get("artists", [])
            if not artists:
                return False, "No artists found"
            
            impersonation_issues = []
            
            for artist in artists:
                artist_name = artist.get("name", "")
                
                # Use moderation service's impersonation detection
                if self.moderation._is_impersonation_attempt(artist_name.lower()):
                    impersonation_issues.append(f"Possible impersonation: {artist_name}")
                
                # Additional checks for specific patterns
                if self._has_impersonation_patterns(artist_name):
                    impersonation_issues.append(f"Impersonation patterns: {artist_name}")
            
            if impersonation_issues:
                return False, "; ".join(impersonation_issues)
            
            return True, "No impersonation detected"
            
        except Exception as e:
            return False, f"Error checking impersonation: {e}"
    
    def _has_impersonation_patterns(self, name: str) -> bool:
        """Check for impersonation patterns"""
        name_lower = name.lower()
        
        for pattern in self.impersonation_patterns:
            if re.search(pattern, name_lower):
                return True
        
        return False
    
    def verify_tiers_reasonable(self, preview: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verify tier distribution is reasonable
        
        Args:
            preview: Preview data dictionary
            
        Returns:
            (reasonable, message) tuple
        """
        try:
            tier_distribution = preview.get("tier_distribution", {})
            total_artists = sum(tier_distribution.values())
            
            if total_artists == 0:
                return False, "No artists found"
            
            issues = []
            
            # Check 1: Not too many legendaries
            legendary_count = tier_distribution.get("legendary", 0)
            legendary_ratio = legendary_count / total_artists
            
            if legendary_ratio > 0.5:  # More than 50% legendaries
                issues.append(f"Too many legendaries: {legendary_count}/{total_artists} ({legendary_ratio:.1%})")
            
            # Check 2: Not all same tier (unless very small pack)
            if total_artists > 3:
                single_tier_count = max(tier_distribution.values())
                if single_tier_count == total_artists:
                    issues.append(f"All artists same tier")
            
            # Check 3: Reasonable distribution
            # Should have some variety in tiers
            tier_variety = sum(1 for count in tier_distribution.values() if count > 0)
            if tier_variety < 2 and total_artists > 5:
                issues.append(f"Low tier variety: {tier_variety} tiers")
            
            # Check 4: No impossible combinations
            # (e.g., all legendary with low popularity)
            avg_popularity = preview.get("avg_popularity", 0)
            if avg_popularity < 30 and legendary_count > 0:
                issues.append(f"Low popularity with legendary tiers")
            
            if issues:
                return False, "; ".join(issues)
            
            return True, "Tier distribution appears reasonable"
            
        except Exception as e:
            return False, f"Error checking tiers: {e}"
    
    def comprehensive_safety_check(self, preview: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run comprehensive safety check
        
        Args:
            preview: Preview data dictionary
            
        Returns:
            Safety check results
        """
        results = {
            "overall_safe": True,
            "checks": {},
            "warnings": [],
            "errors": []
        }
        
        try:
            # Run all safety checks
            checks = [
                ("images_safe", self.safe_images),
                ("artists_real", self.verify_artists_real),
                ("no_impersonation", self.verify_no_impersonation),
                ("tiers_reasonable", self.verify_tiers_reasonable)
            ]
            
            for check_name, check_func in checks:
                try:
                    is_safe, message = check_func(preview)
                    results["checks"][check_name] = {
                        "passed": is_safe,
                        "message": message
                    }
                    
                    if not is_safe:
                        results["overall_safe"] = False
                        results["errors"].append(f"{check_name}: {message}")
                    else:
                        results["warnings"].append(f"{check_name}: {message}")
                        
                except Exception as e:
                    results["checks"][check_name] = {
                        "passed": False,
                        "message": f"Check failed: {e}"
                    }
                    results["overall_safe"] = False
                    results["errors"].append(f"{check_name}: Check failed - {e}")
            
        except Exception as e:
            results["overall_safe"] = False
            results["errors"].append(f"Comprehensive check failed: {e}")
        
        return results


# Global safety check service instance
safety_checks = SafetyCheckService()


# Convenience function for backward compatibility
def safe_images(preview: Dict[str, Any]) -> Tuple[bool, str]:
    """Safe images check (simplified version)"""
    return safety_checks.safe_images(preview)


# Example usage
def example_usage():
    """Example of safety checks usage"""
    
    # Mock preview data
    mock_preview = {
        "name": "Test Pack",
        "artists": [
            {
                "name": "Queen",
                "image": "https://i.ytimg.com/vi/queen/maxresdefault.jpg",
                "subscribers": 1000000,
                "views": 1000000000
            },
            {
                "name": "Led Zeppelin",
                "image": "https://i.ytimg.com/vi/ledzep/maxresdefault.jpg",
                "subscribers": 800000,
                "views": 800000000
            }
        ]
    }
    
    # Run comprehensive safety check
    results = safety_checks.comprehensive_safety_check(mock_preview)
    
    print(f"✅ Overall Safe: {results['overall_safe']}")
    print(f"📊 Checks: {len(results['checks'])}")
    
    for check_name, check_result in results["checks"].items():
        status = "✅" if check_result["passed"] else "❌"
        print(f"   {status} {check_name}: {check_result['message']}")
    
    if results["warnings"]:
        print(f"⚠️ Warnings: {len(results['warnings'])}")
        for warning in results["warnings"]:
            print(f"   • {warning}")
    
    if results["errors"]:
        print(f"❌ Errors: {len(results['errors'])}")
        for error in results["errors"]:
            print(f"   • {error}")


if __name__ == "__main__":
    example_usage()
