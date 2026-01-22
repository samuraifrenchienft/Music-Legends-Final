"""
Card Rendering System

Front Zones (Top → Bottom)
┌──────────────────────────┐
│  Artist Name        Tier │  ← Header band
│──────────────────────────│
│                          │
│      ARTIST IMAGE        │  ← Hero zone (safe crop)
│                          │
│──────────────────────────│
│  Genre        Season     │
│──────────────────────────│
│  Serial • Print # / Cap  │
└──────────────────────────┘

Back never changes per artist.
Only changes by: season, edition, premium run
"""

from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from schemas.card_canonical import CanonicalCard, CardTier, FrameStyle
import os
import io

class CardRenderingSystem:
    """
    Renders canonical cards into visual representations.
    Handles front zones and back design.
    """
    
    def __init__(self):
        self.card_width = 300
        self.card_height = 420
        self.corner_radius = 15
        
        # Zone dimensions (relative to card size)
        self.header_height = int(self.card_height * 0.15)  # 15%
        self.hero_height = int(self.card_height * 0.55)    # 55%
        self.footer_height = int(self.card_height * 0.30)  # 30%
        
        # Colors and styling
        self.tier_colors = {
            CardTier.COMMUNITY: "#E8E8E8",
            CardTier.GOLD: "#FFD700",
            CardTier.PLATINUM: "#C0C0C0",
            CardTier.LEGENDARY: "#9400D3"
        }
        
        self.frame_styles = {
            FrameStyle.LUX_BLACK: "#0B0B0B",
            FrameStyle.LUX_WHITE: "#FFFFFF",
            FrameStyle.CREATOR: "#FF6B6B",
            FrameStyle.SYSTEM: "#4ECDC4"
        }
        
        # Fonts (fallback to default if custom fonts not available)
        try:
            self.font_title = ImageFont.truetype("arial.ttf", 24)
            self.font_header = ImageFont.truetype("arial.ttf", 18)
            self.font_body = ImageFont.truetype("arial.ttf", 14)
            self.font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            self.font_title = ImageFont.load_default()
            self.font_header = ImageFont.load_default()
            self.font_body = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
    
    def render_card_front(self, card: CanonicalCard) -> Image.Image:
        """Render the front of a card with all zones"""
        # Create base card
        card_img = Image.new('RGB', (self.card_width, self.card_height), "white")
        draw = ImageDraw.Draw(card_img)
        
        # Get colors
        tier_color = self.tier_colors.get(CardTier(card.rarity["tier"]), "#E8E8E8")
        frame_color = self.frame_styles.get(FrameStyle(card.presentation["frame_style"]), "#0B0B0B")
        
        # Draw rounded corners
        self._draw_rounded_rectangle(draw, card_img, frame_color)
        
        # Header band
        self._draw_header_band(draw, card, tier_color)
        
        # Hero zone (artist image)
        self._draw_hero_zone(draw, card)
        
        # Footer zones
        self._draw_footer_zones(draw, card, tier_color)
        
        return card_img
    
    def render_card_back(self, card: CanonicalCard) -> Image.Image:
        """Render the back of a card (system-level design)"""
        card_img = Image.new('RGB', (self.card_width, self.card_height), "#1a1a1a")
        draw = ImageDraw.Draw(card_img)
        
        # Draw frame
        self._draw_rounded_rectangle(draw, card_img, "#FFD700")
        
        # Center emblem/pattern
        self._draw_back_emblem(draw, card)
        
        # Season and game name
        season_text = f"Season {card.identity['season']}"
        game_text = "Music Legends"
        
        # Draw text at bottom
        text_bbox = draw.textbbox((0, 0), season_text, font=self.font_body)
        text_width = text_bbox[2] - text_bbox[0]
        text_x = (self.card_width - text_width) // 2
        text_y = self.card_height - 40
        
        draw.text((text_x, text_y), season_text, fill="white", font=self.font_body)
        
        # Game name below season
        game_bbox = draw.textbbox((0, 0), game_text, font=self.font_small)
        game_width = game_bbox[2] - game_bbox[0]
        game_x = (self.card_width - game_width) // 2
        draw.text((game_x, text_y + 20), game_text, fill="#CCCCCC", font=self.font_small)
        
        return card_img
    
    def _draw_rounded_rectangle(self, draw: ImageDraw.Draw, img: Image.Image, color: str):
        """Draw rounded rectangle frame"""
        # Simple rounded rectangle using PIL
        draw.rectangle([0, 0, self.card_width, self.card_height], outline=color, width=3)
        
        # Add corner decorations for premium tiers
        if CardTier(self.tier_colors.get(color, CardTier.COMMUNITY)) in [CardTier.PLATINUM, CardTier.LEGENDARY]:
            corner_size = 20
            # Top-left corner
            draw.arc([0, 0, corner_size*2, corner_size*2], 180, 270, fill=color, width=3)
            # Top-right corner
            draw.arc([self.card_width-corner_size*2, 0, self.card_width, corner_size*2], 270, 360, fill=color, width=3)
            # Bottom-left corner
            draw.arc([0, self.card_height-corner_size*2, corner_size*2, self.card_height], 90, 180, fill=color, width=3)
            # Bottom-right corner
            draw.arc([self.card_width-corner_size*2, self.card_height-corner_size*2, self.card_width, self.card_height], 0, 90, fill=color, width=3)
    
    def _draw_header_band(self, draw: ImageDraw.Draw, card: CanonicalCard, tier_color: str):
        """Draw header band with artist name and tier"""
        # Header background
        draw.rectangle([3, 3, self.card_width-3, self.header_height], fill=tier_color)
        
        # Artist name (left side)
        artist_name = card.artist["name"]
        if len(artist_name) > 15:
            artist_name = artist_name[:12] + "..."
        
        draw.text((10, 8), artist_name, fill="white", font=self.font_header)
        
        # Tier (right side)
        tier_text = card.get_rarity_display().upper()
        tier_bbox = draw.textbbox((0, 0), tier_text, font=self.font_header)
        tier_width = tier_bbox[2] - tier_bbox[0]
        tier_x = self.card_width - tier_width - 10
        
        draw.text((tier_x, 8), tier_text, fill="white", font=self.font_header)
    
    def _draw_hero_zone(self, draw: ImageDraw.Draw, card: CanonicalCard):
        """Draw hero zone with artist image"""
        hero_y = self.header_height
        hero_bottom = hero_y + self.hero_height
        
        # Draw border for hero zone
        draw.rectangle([3, hero_y, self.card_width-3, hero_bottom], outline="#CCCCCC", width=1)
        
        # Placeholder for artist image (in real implementation, load and resize image)
        # For now, draw a placeholder with artist name
        placeholder_text = "ARTIST IMAGE"
        text_bbox = draw.textbbox((0, 0), placeholder_text, font=self.font_title)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_x = (self.card_width - text_width) // 2
        text_y = hero_y + (self.hero_height - text_height) // 2
        
        draw.text((text_x, text_y), placeholder_text, fill="#666666", font=self.font_title)
        
        # Add artist name below placeholder
        artist_text = card.artist["name"]
        artist_bbox = draw.textbbox((0, 0), artist_text, font=self.font_body)
        artist_width = artist_bbox[2] - artist_bbox[0]
        artist_x = (self.card_width - artist_width) // 2
        
        draw.text((artist_x, text_y + text_height + 10), artist_text, fill="#333333", font=self.font_body)
    
    def _draw_footer_zones(self, draw: ImageDraw.Draw, card: CanonicalCard, tier_color: str):
        """Draw footer zones with genre, season, and serial info"""
        footer_y = self.header_height + self.hero_height
        
        # Genre and season line
        genre_season_y = footer_y + 10
        genre_text = card.artist["primary_genre"].title()
        season_text = f"S{card.identity['season']}"
        
        # Genre (left)
        draw.text((10, genre_season_y), genre_text, fill="#333333", font=self.font_body)
        
        # Season (right)
        season_bbox = draw.textbbox((0, 0), season_text, font=self.font_body)
        season_width = season_bbox[2] - season_bbox[0]
        season_x = self.card_width - season_width - 10
        
        draw.text((season_x, genre_season_y), season_text, fill="#333333", font=self.font_body)
        
        # Divider line
        draw.line([10, genre_season_y + 25, self.card_width-10, genre_season_y + 25], fill="#CCCCCC", width=1)
        
        # Serial and print info
        serial_y = genre_season_y + 35
        serial_text = card.identity["serial"]
        print_text = card.get_print_display()
        
        # Serial (left)
        draw.text((10, serial_y), serial_text, fill="#333333", font=self.font_small)
        
        # Print info (right)
        print_bbox = draw.textbbox((0, 0), print_text, font=self.font_small)
        print_width = print_bbox[2] - print_bbox[0]
        print_x = self.card_width - print_width - 10
        
        draw.text((print_x, serial_y), print_text, fill="#666666", font=self.font_small)
        
        # Special badges
        if card.presentation["badge_icons"]:
            badge_y = serial_y + 20
            badge_x = 10
            for badge in card.presentation["badge_icons"][:3]:  # Max 3 badges
                badge_text = f"[{badge.upper()}]"
                draw.text((badge_x, badge_y), badge_text, fill=tier_color, font=self.font_small)
                badge_x += 60
    
    def _draw_back_emblem(self, draw: ImageDraw.Draw, card: CanonicalCard):
        """Draw emblem/pattern on card back"""
        center_x = self.card_width // 2
        center_y = self.card_height // 2
        
        # Draw circular emblem
        emblem_radius = 60
        draw.ellipse([center_x - emblem_radius, center_y - emblem_radius,
                     center_x + emblem_radius, center_y + emblem_radius],
                    outline="#FFD700", width=3)
        
        # Draw "ML" in center
        ml_text = "ML"
        ml_bbox = draw.textbbox((0, 0), ml_text, font=self.font_title)
        ml_width = ml_bbox[2] - ml_bbox[0]
        ml_height = ml_bbox[3] - ml_bbox[1]
        
        ml_x = center_x - ml_width // 2
        ml_y = center_y - ml_height // 2
        
        draw.text((ml_x, ml_y), ml_text, fill="#FFD700", font=self.font_title)
        
        # Add season indicator
        season_text = f"S{card.identity['season']}"
        season_bbox = draw.textbbox((0, 0), season_text, font=self.font_small)
        season_width = season_bbox[2] - season_bbox[0]
        season_x = center_x - season_width // 2
        season_y = center_y + emblem_radius + 10
        
        draw.text((season_x, season_y), season_text, fill="#CCCCCC", font=self.font_small)
    
    def render_card_to_bytes(self, card: CanonicalCard, front: bool = True) -> bytes:
        """Render card and return as bytes for Discord"""
        if front:
            img = self.render_card_front(card)
        else:
            img = self.render_card_back(card)
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        return img_bytes.getvalue()
    
    def create_card_embed(self, card: CanonicalCard, show_front: bool = True) -> Dict[str, Any]:
        """Create Discord embed for card display"""
        tier = CardTier(card.rarity["tier"])
        color = self._get_discord_color(tier)
        
        embed_data = {
            "title": f"🎴 {card.artist['name']}",
            "description": f"**{card.get_rarity_display()}** • {card.artist['primary_genre'].title()}",
            "color": color
        }
        
        # Card details
        embed_data["fields"] = [
            {
                "name": "📊 Card Info",
                "value": f"**Serial:** {card.identity['serial']}\n"
                        f"**Print:** {card.get_print_display()}\n"
                        f"**Season:** {card.identity['season']}",
                "inline": True
            },
            {
                "name": "🎨 Artist",
                "value": f"**Name:** {card.artist['name']}\n"
                        f"**Genre:** {card.artist['primary_genre']}\n"
                        f"**Source:** {card.artist['source'].title()}",
                "inline": True
            }
        ]
        
        # Special badges
        if card.presentation["badge_icons"]:
            badge_text = " ".join([f"🏆 {badge.title()}" for badge in card.presentation["badge_icons"]])
            embed_data["fields"].append({
                "name": "🏆 Badges",
                "value": badge_text,
                "inline": False
            })
        
        # Hero card indicator
        if card.is_hero_card():
            embed_data["fields"].append({
                "name": "⭐ Hero Card",
                "value": "Selected for premium hero slot with boosted artist selection!",
                "inline": False
            })
        
        embed_data["footer"] = {
            "text": f"Card ID: {card.card_id[:8]}... | Serial: {card.identity['serial']}"
        }
        
        return embed_data
    
    def _get_discord_color(self, tier: CardTier) -> int:
        """Convert tier color to Discord color integer"""
        color_map = {
            CardTier.COMMUNITY: 0xC0C0C0,  # Light grey
            CardTier.GOLD: 0xFFD700,       # Gold
            CardTier.PLATINUM: 0xE5E4E2,    # Platinum
            CardTier.LEGENDARY: 0x800080   # Purple
        }
        return color_map.get(tier, 0xC0C0C0)

# Global card rendering system instance
card_renderer = CardRenderingSystem()

def render_card_front(card: CanonicalCard) -> Image.Image:
    """Render card front"""
    return card_renderer.render_card_front(card)

def render_card_back(card: CanonicalCard) -> Image.Image:
    """Render card back"""
    return card_renderer.render_card_back(card)

def create_card_embed(card: CanonicalCard, show_front: bool = True) -> Dict[str, Any]:
    """Create Discord embed for card"""
    return card_renderer.create_card_embed(card, show_front)
