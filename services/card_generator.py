"""
Card Image Generator
Combines frame + artist photo + badge + stats into final card image
"""
from PIL import Image, ImageDraw, ImageFont
import aiohttp
import io
import os
from typing import Dict, Optional

class CardGenerator:
    def __init__(self):
        self.assets_path = "assets"
        self.frames_path = os.path.join(self.assets_path, "frames")
        self.badges_path = os.path.join(self.assets_path, "badges")
        self.logo_path = os.path.join(self.assets_path, "logo.png")
        
        # Card dimensions
        self.card_width = 600
        self.card_height = 900
        self.artist_image_size = (400, 400)
        self.artist_image_position = (100, 130)
        
        # Font paths (fallback to default if custom not available)
        try:
            self.title_font = ImageFont.truetype("arial.ttf", 36)
            self.stat_font = ImageFont.truetype("arial.ttf", 24)
            self.stat_value_font = ImageFont.truetype("arialbd.ttf", 28)
        except:
            self.title_font = ImageFont.load_default()
            self.stat_font = ImageFont.load_default()
            self.stat_value_font = ImageFont.load_default()
    
    async def generate_card(self, card_data: Dict) -> Optional[bytes]:
        """
        Generate a card image from card data
        
        Args:
            card_data: Dict with keys: name, rarity, image_url, impact, skill, longevity, culture, hype
        
        Returns:
            PNG image as bytes, or None if generation fails
        """
        try:
            # Get tier/rarity
            tier = card_data.get('rarity', 'community').lower()
            
            # Load frame
            frame_path = os.path.join(self.frames_path, f"{tier}_frame.png")
            if not os.path.exists(frame_path):
                print(f"Frame not found: {frame_path}")
                return None
            
            frame = Image.open(frame_path).convert("RGBA")
            
            # Download and resize artist image
            artist_image = await self._download_image(card_data.get('image_url', ''))
            if artist_image:
                artist_image = artist_image.resize(self.artist_image_size, Image.Resampling.LANCZOS)
                # Paste artist image onto frame
                frame.paste(artist_image, self.artist_image_position, artist_image if artist_image.mode == 'RGBA' else None)
            
            # Add artist name at top
            draw = ImageDraw.Draw(frame)
            artist_name = card_data.get('name', 'Unknown Artist')
            
            # Draw artist name (centered at top)
            name_bbox = draw.textbbox((0, 0), artist_name, font=self.title_font)
            name_width = name_bbox[2] - name_bbox[0]
            name_x = (self.card_width - name_width) // 2
            name_y = 50
            
            # Add text shadow for readability
            draw.text((name_x + 2, name_y + 2), artist_name, font=self.title_font, fill=(0, 0, 0, 180))
            draw.text((name_x, name_y), artist_name, font=self.title_font, fill=(255, 255, 255, 255))
            
            # Add stats at bottom
            stats = [
                ("Impact", card_data.get('impact', 0)),
                ("Skill", card_data.get('skill', 0)),
                ("Longevity", card_data.get('longevity', 0)),
                ("Culture", card_data.get('culture', 0)),
                ("Hype", card_data.get('hype', 0))
            ]
            
            stat_y = 560
            stat_line_height = 35
            
            for stat_name, stat_value in stats:
                # Draw stat name
                draw.text((70, stat_y), stat_name, font=self.stat_font, fill=(255, 255, 255, 255))
                # Draw stat value (right-aligned)
                value_text = str(stat_value)
                value_bbox = draw.textbbox((0, 0), value_text, font=self.stat_value_font)
                value_width = value_bbox[2] - value_bbox[0]
                draw.text((530 - value_width, stat_y - 2), value_text, font=self.stat_value_font, fill=(255, 215, 0, 255))
                
                stat_y += stat_line_height
            
            # Add logo at bottom
            if os.path.exists(self.logo_path):
                logo = Image.open(self.logo_path).convert("RGBA")
                logo_width = 180
                logo_height = int(logo.height * (logo_width / logo.width))
                logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                logo_x = (self.card_width - logo_width) // 2
                logo_y = 800
                frame.paste(logo, (logo_x, logo_y), logo)
            
            # Convert to bytes
            output = io.BytesIO()
            frame.save(output, format='PNG')
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            print(f"Error generating card: {e}")
            return None
    
    async def _download_image(self, url: str) -> Optional[Image.Image]:
        """Download image from URL"""
        if not url:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        return Image.open(io.BytesIO(image_data)).convert("RGBA")
        except Exception as e:
            print(f"Error downloading image from {url}: {e}")
        
        return None

# Global instance
card_generator = CardGenerator()
