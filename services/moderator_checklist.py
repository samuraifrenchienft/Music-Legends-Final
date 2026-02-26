# services/moderator_checklist.py
"""
Enhanced Moderator Checklist Service
Comprehensive validation for creator pack approval
"""

from typing import Dict, List, Tuple, Any
from services.safety_checks import safety_checks
from services.creator_moderation import creator_moderation

class ModeratorChecklistService:
    """Service for comprehensive moderator checklist"""
    
    def __init__(self):
        self.safety_checks = safety_checks
        self.moderation = creator_moderation
    
    def run_complete_checklist(self, preview: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run complete moderator checklist
        
        Args:
            preview: Preview data dictionary
            
        Returns:
            Complete checklist results
        """
        results = {
            "overall_passed": True,
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "check_results": {},
            "critical_failures": [],
            "warnings": [],
            "recommendation": "APPROVE"
        }
        
        try:
            # Define all checklist items
            checklist_items = [
                ("roster_matches_genre", self._check_roster_matches_genre),
                ("no_duplicate_artists", self._check_no_duplicate_artists),
                ("no_topic_auto_channels", self._check_no_topic_auto_channels),
                ("images_appropriate", self._check_images_appropriate),
                ("artist_count_valid", self._check_artist_count_valid),
                ("payment_authorized", self._check_payment_authorized),
                ("artists_real", self._check_artists_real),
                ("no_impersonation", self._check_no_impersonation),
                ("tiers_reasonable", self._check_tiers_reasonable),
                ("quality_acceptable", self._check_quality_acceptable),
                ("youtube_data_available", self._check_youtube_data_available),
                ("pack_name_appropriate", self._check_pack_name_appropriate),
                ("genre_consistency", self._check_genre_consistency),
                ("no_inappropriate_content", self._check_no_inappropriate_content)
            ]
            
            # Mark critical checks
            critical_checks = {
                "images_appropriate", "no_impersonation", "no_inappropriate_content",
                "payment_authorized", "artist_count_valid"
            }
            
            # Run each check
            for check_name, check_func in checklist_items:
                results["total_checks"] += 1
                
                try:
                    passed, message, is_critical = check_func(preview)
                    
                    results["check_results"][check_name] = {
                        "passed": passed,
                        "message": message,
                        "critical": is_critical
                    }
                    
                    if passed:
                        results["passed_checks"] += 1
                    else:
                        results["failed_checks"] += 1
                        results["overall_passed"] = False
                        
                        if is_critical or check_name in critical_checks:
                            results["critical_failures"].append(f"{check_name}: {message}")
                        else:
                            results["warnings"].append(f"{check_name}: {message}")
                            
                except Exception as e:
                    results["total_checks"] -= 1
                    results["check_results"][check_name] = {
                        "passed": False,
                        "message": f"Check failed: {e}",
                        "critical": True
                    }
                    results["failed_checks"] += 1
                    results["overall_passed"] = False
                    results["critical_failures"].append(f"{check_name}: Check error - {e}")
            
            # Determine recommendation
            results["recommendation"] = self._determine_recommendation(results)
            
        except Exception as e:
            results["overall_passed"] = False
            results["critical_failures"].append(f"Checklist execution failed: {e}")
            results["recommendation"] = "REJECT"
        
        return results
    
    def _check_roster_matches_genre(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check if roster matches declared genre"""
        try:
            declared_genre = preview.get("genre", "").lower()
            artists = preview.get("artists", [])
            
            if not declared_genre:
                return False, "No genre declared", True
            
            genre_mismatches = []
            genre_matches = 0
            
            for artist in artists:
                artist_genre = artist.get("genre", "").lower()
                if artist_genre and artist_genre != "unknown":
                    if artist_genre == declared_genre:
                        genre_matches += 1
                    else:
                        genre_mismatches.append(artist["name"])
            
            # Allow up to 20% genre mismatch for diversity
            mismatch_ratio = len(genre_mismatches) / len(artists) if artists else 0
            
            if mismatch_ratio > 0.5:  # More than 50% mismatch
                return False, f"Major genre mismatch: {len(genre_mismatches)}/{len(artists)} artists don't match {declared_genre}", False
            elif mismatch_ratio > 0.2:  # 20-50% mismatch
                return True, f"Some genre mismatch: {len(genre_mismatches)}/{len(artists)} artists don't match {declared_genre}", False
            else:
                return True, f"Good genre consistency: {genre_matches}/{len(artists)} artists match {declared_genre}", False
                
        except Exception as e:
            return False, f"Error checking genre consistency: {e}", True
    
    def _check_no_duplicate_artists(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check for duplicate artists"""
        try:
            artists = preview.get("artists", [])
            artist_names = [artist.get("name", "").lower().strip() for artist in artists]
            
            unique_names = set(artist_names)
            duplicates = len(artist_names) - len(unique_names)
            
            if duplicates > 0:
                # Find specific duplicates
                duplicate_names = []
                seen = set()
                for name in artist_names:
                    if name in seen and name not in duplicate_names:
                        duplicate_names.append(name)
                    seen.add(name)
                
                return False, f"Found {duplicates} duplicate artists: {', '.join(duplicate_names)}", True
            else:
                return True, f"No duplicates found in {len(artists)} artists", False
                
        except Exception as e:
            return False, f"Error checking duplicates: {e}", True
    
    def _check_no_topic_auto_channels(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check for topic/auto channels"""
        try:
            artists = preview.get("artists", [])
            banned_keywords = ["topic", "auto", "official", "vevo", "reupload", "free music"]
            problematic_artists = []
            
            for artist in artists:
                artist_name = artist.get("name", "").lower()
                
                for keyword in banned_keywords:
                    if keyword in artist_name:
                        problematic_artists.append(artist["name"])
                        break
            
            if problematic_artists:
                return False, f"Found {len(problematic_artists)} problematic channels: {', '.join(problematic_artists)}", True
            else:
                return True, f"No topic/auto channels found in {len(artists)} artists", False
                
        except Exception as e:
            return False, f"Error checking topic channels: {e}", True
    
    def _check_images_appropriate(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check if images are appropriate"""
        try:
            safe, message = self.safety_checks.safe_images(preview)
            return safe, message, True  # Images are always critical
        except Exception as e:
            return False, f"Error checking images: {e}", True
    
    def _check_artist_count_valid(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check if artist count is valid (5-25)"""
        try:
            artist_count = preview.get("artist_count", 0)
            
            if artist_count < 5:
                return False, f"Too few artists: {artist_count} (minimum 5)", True
            elif artist_count > 25:
                return False, f"Too many artists: {artist_count} (maximum 25)", True
            else:
                return True, f"Valid artist count: {artist_count}", False
                
        except Exception as e:
            return False, f"Error checking artist count: {e}", True
    
    def _check_payment_authorized(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check if payment is authorized"""
        try:
            payment_status = preview.get("payment_status", "")
            
            if payment_status == "authorized":
                return True, "Payment is authorized and ready for capture", False
            elif payment_status == "captured":
                return True, "Payment already captured", False
            else:
                return False, f"Payment not authorized: {payment_status}", True
                
        except Exception as e:
            return False, f"Error checking payment status: {e}", True
    
    def _check_artists_real(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check if artists appear to be real"""
        try:
            real, message = self.safety_checks.verify_artists_real(preview)
            return real, message, False  # Not critical but important
        except Exception as e:
            return False, f"Error verifying artists: {e}", False
    
    def _check_no_impersonation(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check for impersonation attempts"""
        try:
            no_impersonation, message = self.safety_checks.verify_no_impersonation(preview)
            return no_impersonation, message, True  # Impersonation is critical
        except Exception as e:
            return False, f"Error checking impersonation: {e}", True
    
    def _check_tiers_reasonable(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check if tier distribution is reasonable"""
        try:
            reasonable, message = self.safety_checks.verify_tiers_reasonable(preview)
            return reasonable, message, False  # Not critical but important
        except Exception as e:
            return False, f"Error checking tiers: {e}", False
    
    def _check_quality_acceptable(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check if pack quality is acceptable"""
        try:
            quality_score = preview.get("quality_score", 0)
            
            if quality_score >= 40:
                return True, f"Good quality score: {quality_score}/100", False
            elif quality_score >= 20:
                return True, f"Acceptable quality score: {quality_score}/100", False
            else:
                return False, f"Low quality score: {quality_score}/100 (minimum 20)", False
                
        except Exception as e:
            return False, f"Error checking quality: {e}", False
    
    def _check_youtube_data_available(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check if YouTube data is available"""
        try:
            has_youtube_data = preview.get("has_youtube_data", False)
            artists = preview.get("artists", [])
            
            youtube_artists = sum(1 for artist in artists if artist.get("channel_id"))
            
            if has_youtube_data and youtube_artists > 0:
                return True, f"YouTube data available for {youtube_artists}/{len(artists)} artists", False
            else:
                return False, f" Limited YouTube data: {youtube_artists}/{len(artists)} artists have channel data", False
                
        except Exception as e:
            return False, f"Error checking YouTube data: {e}", False
    
    def _check_pack_name_appropriate(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check if pack name is appropriate"""
        try:
            pack_name = preview.get("name", "")
            
            if not pack_name:
                return False, "No pack name provided", True
            
            # Check length
            if len(pack_name) > 60:
                return False, f"Pack name too long: {len(pack_name)} characters (max 60)", True
            
            # Check for inappropriate content
            if self.moderation._is_impersonation_attempt(pack_name.lower()):
                return False, "Pack name suggests impersonation", True
            
            # Check for banned keywords
            banned_keywords = ["official", "vevo", "topic", "reupload"]
            for keyword in banned_keywords:
                if keyword in pack_name.lower():
                    return False, f"Pack name contains banned keyword: {keyword}", True
            
            return True, f"Appropriate pack name: {pack_name}", False
            
        except Exception as e:
            return False, f"Error checking pack name: {e}", True
    
    def _check_genre_consistency(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check genre consistency across artists"""
        try:
            declared_genre = preview.get("genre", "").lower()
            artists = preview.get("artists", [])
            
            if not declared_genre:
                return False, "No genre declared", True
            
            # Count genres
            genre_counts = {}
            for artist in artists:
                artist_genre = artist.get("genre", "").lower()
                if artist_genre and artist_genre != "unknown":
                    genre_counts[artist_genre] = genre_counts.get(artist_genre, 0) + 1
            
            if not genre_counts:
                return False, "No genre data available for artists", False
            
            # Check if declared genre is dominant
            declared_count = genre_counts.get(declared_genre, 0)
            total_count = sum(genre_counts.values())
            
            if declared_count >= total_count * 0.6:  # At least 60%
                return True, f"Good genre consistency: {declared_count}/{total_count} artists match {declared_genre}", False
            else:
                return False, f"Poor genre consistency: only {declared_count}/{total_count} artists match {declared_genre}", False
                
        except Exception as e:
            return False, f"Error checking genre consistency: {e}", False
    
    def _check_no_inappropriate_content(self, preview: Dict[str, Any]) -> Tuple[bool, str, bool]:
        """Check for inappropriate content"""
        try:
            artists = preview.get("artists", [])
            pack_name = preview.get("name", "")
            
            inappropriate_content = []
            
            # Check pack name
            pack_name_lower = pack_name.lower()
            for word in self.moderation.INAPPROPRIATE_CONTENT:
                if word in pack_name_lower:
                    inappropriate_content.append(f"Pack name: {word}")
            
            # Check artist names
            for artist in artists:
                artist_name = artist.get("name", "").lower()
                for word in self.moderation.INAPPROPRIATE_CONTENT:
                    if word in artist_name:
                        inappropriate_content.append(f"Artist {artist['name']}: {word}")
            
            if inappropriate_content:
                return False, f"Inappropriate content found: {'; '.join(inappropriate_content)}", True
            else:
                return True, "No inappropriate content found", True
                
        except Exception as e:
            return False, f"Error checking inappropriate content: {e}", True
    
    def _determine_recommendation(self, results: Dict[str, Any]) -> str:
        """Determine recommendation based on results"""
        try:
            # Critical failures = auto-reject
            if results["critical_failures"]:
                return "REJECT"
            
            # All checks passed = approve
            if results["overall_passed"]:
                return "APPROVE"
            
            # Some failures but no critical = review
            failed_count = results["failed_checks"]
            total_count = results["total_checks"]
            
            if failed_count <= 2 and total_count > 5:
                return "REVIEW"
            else:
                return "REJECT"
                
        except Exception:
            return "REJECT"
    
    def get_checklist_summary(self, preview: Dict[str, Any]) -> str:
        """Get formatted checklist summary"""
        try:
            results = self.run_complete_checklist(preview)
            
            summary = f"📋 Moderator Checklist Summary\n"
            summary += f"📊 Total Checks: {results['total_checks']}\n"
            summary += f"✅ Passed: {results['passed_checks']}\n"
            summary += f"❌ Failed: {results['failed_checks']}\n"
            summary += f"🎯 Overall: {'✅ PASSED' if results['overall_passed'] else '❌ FAILED'}\n"
            summary += f"💡 Recommendation: {results['recommendation']}\n\n"
            
            # Show critical failures
            if results["critical_failures"]:
                summary += "🚨 Critical Failures:\n"
                for failure in results["critical_failures"]:
                    summary += f"   • {failure}\n"
                summary += "\n"
            
            # Show warnings
            if results["warnings"]:
                summary += "⚠️ Warnings:\n"
                for warning in results["warnings"]:
                    summary += f"   • {warning}\n"
                summary += "\n"
            
            # Show passed checks
            passed_checks = [name for name, result in results["check_results"].items() if result["passed"]]
            if passed_checks:
                summary += "✅ Passed Checks:\n"
                for check in passed_checks:
                    summary += f"   • {check}\n"
            
            return summary
            
        except Exception as e:
            return f"❌ Error generating checklist summary: {e}"


# Global moderator checklist service instance
moderator_checklist = ModeratorChecklistService()


# Example usage
def example_usage():
    """Example of moderator checklist usage"""
    
    # Mock preview data
    mock_preview = {
        "name": "Rock Legends Pack",
        "genre": "Rock",
        "payment_status": "authorized",
        "artist_count": 8,
        "quality_score": 75,
        "has_youtube_data": True,
        "artists": [
            {
                "name": "Queen",
                "genre": "Rock",
                "image": "https://example.com/queen.jpg",
                "channel_id": "UC123",
                "subscribers": 1000000
            },
            {
                "name": "Led Zeppelin",
                "genre": "Rock",
                "image": "https://example.com/led.jpg",
                "channel_id": "UC456",
                "subscribers": 800000
            }
        ]
    }
    
    # Run complete checklist
    results = moderator_checklist.run_complete_checklist(mock_preview)
    
    print(f"🎯 Overall Passed: {results['overall_passed']}")
    print(f"📊 Total Checks: {results['total_checks']}")
    print(f"✅ Passed: {results['passed_checks']}")
    print(f"❌ Failed: {results['failed_checks']}")
    print(f"💡 Recommendation: {results['recommendation']}")
    
    if results["critical_failures"]:
        print(f"🚨 Critical Failures: {len(results['critical_failures'])}")
        for failure in results["critical_failures"]:
            print(f"   • {failure}")
    
    # Get summary
    summary = moderator_checklist.get_checklist_summary(mock_preview)
    print(f"\n📋 Summary:\n{summary}")


if __name__ == "__main__":
    example_usage()
