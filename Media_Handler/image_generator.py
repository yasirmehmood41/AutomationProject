"""Image generation component for Media Handler.

This module provides integrations with various image generation services and APIs
while maintaining backward compatibility with existing code.
"""

import os
import logging
import json
import random
import base64
import requests
from typing import Optional, Dict, List, Union, Tuple
from pathlib import Path
import tempfile
from PIL import Image, ImageDraw, ImageFont

# Import AI integration hub
try:
    from Content_Engine.ai_integrations import create_api_hub
    from yaml import safe_load
    
    config_path = Path("config.yaml")
    config = {}
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = safe_load(f)
    ai_hub = create_api_hub(config.get('ai_providers', {}))
except Exception as e:
    ai_hub = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TODO: Add support for additional image providers (e.g., DALL·E, Midjourney, local GANs)
# TODO: Add more robust error handling for cache/image generation failures

class ImageGenerator:
    """Image generator for video scenes."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize image generator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.cache_dir = self._get_cache_dir()
        self.default_size = (1920, 1080)
        self.dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        
        # Initialize AI Hub
        self.ai_hub = ai_hub
        self.default_provider = self.config.get('ai_providers', {}).get('default_provider', 'stability')
        
    def _get_cache_dir(self) -> Path:
        """Get cache directory for storing generated images."""
        cache_dir = Path(self.config.get('cache_dir', 'cache/images'))
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir
        
    def generate_image(self, 
                      prompt: str, 
                      size: Tuple[int, int] = None,
                      style: str = "modern",
                      negative_prompt: str = None,
                      cache_key: str = None) -> Optional[str]:
        """Generate image based on prompt.
        
        Args:
            prompt: Image description prompt
            size: Image size (width, height)
            style: Visual style for the image
            negative_prompt: Elements to exclude from the image
            cache_key: Key for caching generated image
            
        Returns:
            Path to the generated image
        """
        import hashlib
        
        size = size or self.default_size
        
        # Create cache key if not provided
        if not cache_key:
            prompt_hash = hashlib.md5(f"{prompt}_{size[0]}x{size[1]}_{style}".encode()).hexdigest()
            cache_key = f"img_{prompt_hash}.png"
            
        # Check cache first
        cache_path = self.cache_dir / cache_key
        if cache_path.exists():
            logger.info(f"Using cached image: {cache_path}")
            return str(cache_path)
            
        # Generate enhanced prompt based on style
        enhanced_prompt = self._enhance_prompt(prompt, style)
        
        # Try using AI Hub for generation
        if self.ai_hub and not self.dev_mode:
            try:
                # Call the image generation service
                output_path = str(cache_path)
                self.ai_hub.generate_image(
                    enhanced_prompt,
                    provider=self.default_provider,
                    output_path=output_path,
                    negative_prompt=negative_prompt,
                    width=size[0],
                    height=size[1]
                )
                
                if os.path.exists(output_path):
                    logger.info(f"Generated image with AI: {output_path}")
                    return output_path
            except Exception as e:
                logger.error(f"Error generating image with AI: {e}")
                
        # Fallback to local placeholder generation
        return self._generate_placeholder_image(enhanced_prompt, size, style, cache_path)
    
    def _enhance_prompt(self, prompt: str, style: str) -> str:
        """Enhance prompt based on style for better image generation.
        
        Args:
            prompt: Original image prompt
            style: Visual style
            
        Returns:
            Enhanced prompt
        """
        style_prompts = {
            "modern": "modern, clean design, minimalist, professional lighting, high quality, 4k",
            "corporate": "corporate, professional, business setting, formal, office environment, clean lighting",
            "creative": "creative, artistic, vibrant colors, dynamic composition, imaginative, eye-catching",
            "tech": "futuristic, high-tech, digital interface, neon accents, dark background, technological",
            "casual": "casual, warm colors, friendly atmosphere, soft lighting, approachable, relaxed setting"
        }
        
        style_suffix = style_prompts.get(style.lower(), style_prompts["modern"])
        
        # Clean up the prompt
        clean_prompt = prompt.strip().rstrip('.').strip('"\'')
        
        # Combine with style
        return f"{clean_prompt}, {style_suffix}"
        
    def _generate_placeholder_image(self, 
                                   prompt: str, 
                                   size: Tuple[int, int],
                                   style: str, 
                                   output_path: Path) -> str:
        """Generate a placeholder image for development mode.
        
        Args:
            prompt: Image description prompt
            size: Image size (width, height)
            style: Visual style
            output_path: Path to save the generated image
            
        Returns:
            Path to the generated image
        """
        logger.info(f"Generating placeholder image for: {prompt}")
        
        # Only add overlay if dev_mode is True
        if not self.dev_mode:
            # In production, generate a blank or background-only image without overlays
            img = Image.new('RGB', size, color=(30, 30, 30))
            img.save(output_path)
            return str(output_path)
        
        # Set style-based colors
        style_colors = {
            "modern": {"bg": (240, 240, 240), "fg": (40, 40, 40), "accent": (0, 120, 212)},
            "corporate": {"bg": (245, 245, 245), "fg": (30, 30, 30), "accent": (0, 80, 160)},
            "creative": {"bg": (255, 240, 245), "fg": (40, 40, 40), "accent": (230, 80, 120)},
            "tech": {"bg": (20, 30, 40), "fg": (220, 220, 220), "accent": (0, 200, 255)},
            "casual": {"bg": (255, 250, 240), "fg": (60, 60, 60), "accent": (255, 150, 50)}
        }
        
        colors = style_colors.get(style.lower(), style_colors["modern"])
        
        # Create a new image with style-appropriate color
        img = Image.new('RGB', size, color=colors["bg"])
        draw = ImageDraw.Draw(img)
        
        # Try to load a font
        try:
            font = ImageFont.truetype("arial.ttf", size[1] // 20)
            small_font = ImageFont.truetype("arial.ttf", size[1] // 30)
        except IOError:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Add style-based design elements
        if style == "modern":
            # Add minimalist accent line
            line_y = size[1] // 3
            draw.rectangle([(0, line_y), (size[0], line_y + size[1]//40)], fill=colors["accent"])
            
        elif style == "tech":
            # Add grid lines
            for x in range(0, size[0], size[0]//20):
                draw.line([(x, 0), (x, size[1])], fill=(40, 60, 80), width=1)
            for y in range(0, size[1], size[1]//20):
                draw.line([(0, y), (size[0], y)], fill=(40, 60, 80), width=1)
                
            # Add "digital" accents
            for _ in range(5):
                x = random.randint(0, size[0])
                y = random.randint(0, size[1])
                w = random.randint(size[0]//20, size[0]//10)
                h = random.randint(size[1]//20, size[1]//10)
                draw.rectangle([(x, y), (x+w, y+h)], 
                              outline=colors["accent"], 
                              width=2)
                
        elif style == "creative":
            # Add colorful elements
            for _ in range(7):
                x = random.randint(0, size[0])
                y = random.randint(0, size[1])
                r = random.randint(size[0]//30, size[0]//15)
                color = (
                    random.randint(200, 255),
                    random.randint(50, 200),
                    random.randint(100, 255)
                )
                draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=color)
                
        elif style == "corporate":
            # Add professional header and footer bars
            draw.rectangle([(0, 0), (size[0], size[1]//10)], fill=colors["accent"])
            draw.rectangle([(0, size[1]-size[1]//15), (size[0], size[1])], fill=colors["accent"])
            
        elif style == "casual":
            # Add rounded corners effect and soft gradient
            overlay = Image.new('RGB', size, color=(255, 255, 255))
            overlay_draw = ImageDraw.Draw(overlay)
            
            # Gradient effect
            for y in range(size[1]):
                color_value = int(240 + (y / size[1]) * 15)
                overlay_draw.line([(0, y), (size[0], y)], 
                                 fill=(color_value, color_value - 10, color_value - 20))
                
            img = Image.blend(img, overlay, 0.5)
            draw = ImageDraw.Draw(img)
        
        # Add prompt as text (centered)
        import textwrap
        wrapped_text = textwrap.wrap(prompt, width=30)
        
        # Use Pillow 10+ compatible text size calculation
        def get_text_size(font, text):
            bbox = font.getbbox(text)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return width, height

        # Background box for text
        text_y = size[1] // 2 - (len(wrapped_text) * size[1] // 30)
        for i, line in enumerate(wrapped_text):
            line_y = text_y + i * size[1] // 20
            text_w, _ = get_text_size(font, line)
            draw.text(
                ((size[0] - text_w) // 2, line_y),
                line,
                font=font,
                fill=colors["fg"]
            )
        
        # Add "DEV MODE" label
        dev_text = "DEVELOPMENT MODE IMAGE"
        dev_w, dev_h = get_text_size(small_font, dev_text)
        draw.rectangle(
            [(size[0] - dev_w - 20, 10), (size[0] - 10, 10 + dev_h + 10)],
            fill=(200, 200, 200, 150)
        )
        draw.text(
            (size[0] - dev_w - 15, 15),
            dev_text,
            font=small_font,
            fill=(100, 100, 100)
        )
        
        # Save image
        img.save(output_path)
        logger.info(f"Generated placeholder image: {output_path}")
        
        return str(output_path)
    
    def enhance_image(self, 
                     image_path: str, 
                     style: str = "modern",
                     overlay_text: str = None) -> str:
        """Enhance existing image with style-specific filters and overlays.
        
        Args:
            image_path: Path to the source image
            style: Visual style to apply
            overlay_text: Optional text to overlay on the image
            
        Returns:
            Path to the enhanced image
        """
        if not os.path.exists(image_path):
            logger.error(f"Source image not found: {image_path}")
            return None
            
        import hashlib
        source_hash = hashlib.md5(open(image_path, 'rb').read()).hexdigest()
        overlay_hash = hashlib.md5(str(overlay_text or "").encode()).hexdigest()[:8]
        
        # Create output filename
        output_filename = f"enhanced_{source_hash}_{style}_{overlay_hash}.png"
        output_path = self.cache_dir / output_filename
        
        # Check cache
        if output_path.exists():
            logger.info(f"Using cached enhanced image: {output_path}")
            return str(output_path)
        
        try:
            # Open source image
            img = Image.open(image_path)
            
            # Resize if needed
            if img.size != self.default_size:
                img = img.resize(self.default_size, Image.LANCZOS)
            
            # Apply style-specific enhancements
            img = self._apply_style_effects(img, style)
            
            # Add overlay text if provided
            if overlay_text:
                img = self._add_text_overlay(img, overlay_text, style)
            
            # Save enhanced image
            img.save(output_path)
            logger.info(f"Enhanced image saved: {output_path}")
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error enhancing image: {e}")
            return image_path
    
    def _apply_style_effects(self, img: Image.Image, style: str) -> Image.Image:
        """Apply style-specific visual effects to image.
        
        Args:
            img: Source PIL image
            style: Visual style to apply
            
        Returns:
            Modified PIL image
        """
        from PIL import ImageFilter, ImageEnhance
        
        # Apply style-specific effects
        if style == "modern":
            # Increase contrast slightly, add small amount of sharpness
            img = ImageEnhance.Contrast(img).enhance(1.1)
            img = ImageEnhance.Sharpness(img).enhance(1.2)
            
        elif style == "corporate":
            # Desaturate slightly, increase brightness
            img = ImageEnhance.Color(img).enhance(0.9)
            img = ImageEnhance.Brightness(img).enhance(1.1)
            
        elif style == "creative":
            # Increase saturation, contrast, and add slight blur
            img = ImageEnhance.Color(img).enhance(1.3)
            img = ImageEnhance.Contrast(img).enhance(1.15)
            img = img.filter(ImageFilter.GaussianBlur(0.5))
            
        elif style == "tech":
            # Add blue tone, increase contrast, darken
            img = ImageEnhance.Color(img).enhance(0.8)
            img = ImageEnhance.Contrast(img).enhance(1.2)
            img = ImageEnhance.Brightness(img).enhance(0.95)
            
            # Add blue tint
            from PIL import ImageChops
            blue_layer = Image.new('RGB', img.size, (0, 20, 50))
            img = ImageChops.multiply(img, blue_layer)
            
        elif style == "casual":
            # Warm tint, soften
            img = ImageEnhance.Color(img).enhance(1.1)
            img = img.filter(ImageFilter.UnsharpMask(radius=1, percent=50))
            
            # Add warm tint
            from PIL import ImageChops
            warm_layer = Image.new('RGB', img.size, (255, 250, 230))
            img = ImageChops.blend(img, warm_layer, 0.1)
        
        return img
    
    def _add_text_overlay(self, img: Image.Image, text: str, style: str) -> Image.Image:
        """Add text overlay to image based on style.
        
        Args:
            img: Source PIL image
            text: Text to overlay
            style: Visual style
            
        Returns:
            Modified PIL image
        """
        draw = ImageDraw.Draw(img)
        
        # Set style-based text colors and positions
        style_text = {
            "modern": {"color": (255, 255, 255), "bg": (0, 0, 0, 180), "position": "bottom"},
            "corporate": {"color": (255, 255, 255), "bg": (0, 80, 160, 200), "position": "top"},
            "creative": {"color": (255, 255, 255), "bg": (230, 80, 120, 180), "position": "center"},
            "tech": {"color": (0, 200, 255), "bg": (0, 0, 0, 200), "position": "bottom"},
            "casual": {"color": (80, 60, 40), "bg": (255, 255, 255, 180), "position": "bottom"}
        }
        
        text_style = style_text.get(style.lower(), style_text["modern"])
        
        # Try to load a font
        try:
            font_size = img.height // 15
            font = ImageFont.truetype("arial.ttf", font_size)
        except IOError:
            font = ImageFont.load_default()
        
        # Wrap text to fit image width
        import textwrap
        max_width = int(img.width * 0.8) // font_size
        wrapped_text = textwrap.wrap(text, width=max_width)
        
        # Calculate text dimensions (Pillow 10+ compatible)
        def get_text_size(font, text):
            bbox = font.getbbox(text)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            return width, height

        total_text_height = sum(get_text_size(font, line)[1] for line in wrapped_text)
        line_heights = [get_text_size(font, line)[1] for line in wrapped_text]
        text_widths = [get_text_size(font, line)[0] for line in wrapped_text]
        
        # Determine text position
        padding = img.height // 40
        if text_style["position"] == "bottom":
            text_y = img.height - total_text_height - padding * 2
        elif text_style["position"] == "top":
            text_y = padding
        else:  # center
            text_y = (img.height - total_text_height) // 2
        
        # Create text background
        bg_overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg_overlay)
        
        # Draw background for text
        bg_y = text_y - padding
        bg_height = total_text_height + padding * 2
        
        bg_draw.rectangle(
            [(0, bg_y), (img.width, bg_y + bg_height)],
            fill=text_style["bg"]
        )
        
        # Composite background onto image
        img = Image.alpha_composite(img.convert('RGBA'), bg_overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # Draw text lines
        current_y = text_y
        for i, line in enumerate(wrapped_text):
            text_width = text_widths[i]
            text_x = (img.width - text_width) // 2
            draw.text((text_x, current_y), line, font=font, fill=text_style["color"])
            current_y += line_heights[i]
        
        return img

# TODO: Add more test cases and integration tests for image generation workflows.
