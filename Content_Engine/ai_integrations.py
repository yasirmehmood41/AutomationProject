"""AI API Integrations for Content Engine.

This module provides integrations with various AI APIs for content generation,
while maintaining compatibility with the existing codebase.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables for API keys
load_dotenv()

class AIProvider:
    """Base class for AI API providers.
    
    TODO: Add support for rate limiting, retry logic, and provider health checks.
    """
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """Initialize the AI provider.
        
        Args:
            api_key: API key for the service.
            **kwargs: Additional provider-specific parameters.
        """
        self.api_key = api_key or os.getenv(f"{self.__class__.__name__.upper()}_API_KEY")
        self.is_dev_mode = os.getenv("DEV_MODE", "true").lower() == "true"
        self.mock_responses_dir = Path("Content_Engine/mock_responses")
        
        # Ensure mock responses directory exists
        if self.is_dev_mode:
            self.mock_responses_dir.mkdir(parents=True, exist_ok=True)
        
    def generate_content(self, prompt: str, **kwargs) -> str:
        """Generate content using the AI provider.
        
        Args:
            prompt: The prompt to send to the API.
            **kwargs: Additional parameters.
            
        Returns:
            Generated content as text.
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_mock_response(self, prompt_hash: str, prompt_type: str) -> Optional[str]:
        """Get mock response for development mode."""
        if not self.is_dev_mode:
            return None
            
        mock_file = self.mock_responses_dir / f"{prompt_type}_{prompt_hash}.json"
        if mock_file.exists():
            try:
                with open(mock_file, 'r') as f:
                    return json.load(f)["response"]
            except Exception as e:
                logger.warning(f"Error loading mock response: {e}")
                
        return None
        
    def save_mock_response(self, prompt: str, response: str, prompt_type: str):
        """Save mock response for development mode."""
        if not self.is_dev_mode:
            return
            
        import hashlib
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        mock_file = self.mock_responses_dir / f"{prompt_type}_{prompt_hash}.json"
        try:
            with open(mock_file, 'w') as f:
                json.dump({
                    "prompt": prompt,
                    "response": response,
                    "type": prompt_type
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving mock response: {e}")


class OpenAIProvider(AIProvider):
    """OpenAI API provider integration.
    
    TODO: Add streaming support and error parsing for OpenAI API responses.
    """
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "gpt-4-turbo-preview",
                 temperature: float = 0.7,
                 **kwargs):
        """Initialize the OpenAI provider.
        
        Args:
            api_key: OpenAI API key.
            model: Model to use for content generation.
            temperature: Controls randomness in output.
            **kwargs: Additional provider-specific parameters.
        """
        super().__init__(api_key, **kwargs)
        self.model = model
        self.temperature = temperature
        self.api_url = "https://api.openai.com/v1/chat/completions"
        
    def generate_content(self, prompt: str, prompt_type: str = "script", **kwargs) -> str:
        """Generate content using the OpenAI API.
        
        Args:
            prompt: The prompt to send to the API.
            prompt_type: Type of prompt (for mock responses).
            **kwargs: Additional parameters.
            
        Returns:
            Generated content as text.
        """
        import hashlib
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        # Check for mock response in dev mode
        mock_response = self.get_mock_response(prompt_hash, prompt_type)
        if mock_response:
            logger.info(f"Using mock response for {prompt_type}")
            return mock_response
            
        if self.is_dev_mode:
            # Generate placeholder content in dev mode
            logger.info(f"DEV MODE: Would call OpenAI API with prompt: {prompt[:100]}...")
            mock_content = self._generate_placeholder_content(prompt, prompt_type)
            self.save_mock_response(prompt, mock_content, prompt_type)
            return mock_content
            
        # Real API call for production
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            **kwargs
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            self.save_mock_response(prompt, content, prompt_type)
            return content
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return self._generate_placeholder_content(prompt, prompt_type)
            
    def _generate_placeholder_content(self, prompt: str, prompt_type: str) -> str:
        """Generate placeholder content for development mode."""
        if prompt_type == "script":
            return """Scene 1: Introduction
[Show modern cityscape]
Welcome to our exploration of cutting-edge technology that's transforming how we interact with the digital world.

Scene 2: The Problem
[Display person looking frustrated at complicated interface]
In today's fast-paced environment, managing multiple systems can be overwhelming and time-consuming.

Scene 3: Solution Overview
[Show simplified dashboard interface]
Our automation solution streamlines these processes, creating a seamless workflow that saves time and reduces errors.

Scene 4: Key Features
[Display animated feature highlights]
With intelligent scheduling, smart notifications, and customizable workflows, you gain complete control over your digital ecosystem.

Scene 5: Real World Benefits
[Show satisfied users with metrics]
Users report saving an average of 15 hours per week, with a 40% reduction in manual errors.

Scene 6: Call to Action
[Clean screen with product logo]
Ready to transform your workflow? Visit our website today to learn more and start your free trial."""
        
        elif prompt_type == "scene_data":
            return json.dumps([
                {
                    "title": "Introduction",
                    "text": "Welcome to our exploration of cutting-edge technology that's transforming how we interact with the digital world.",
                    "visual_prompt": "modern cityscape",
                    "duration": 5.0,
                    "transition": "fade"
                },
                {
                    "title": "The Problem",
                    "text": "In today's fast-paced environment, managing multiple systems can be overwhelming and time-consuming.",
                    "visual_prompt": "person looking frustrated at complicated interface",
                    "duration": 6.0,
                    "transition": "dissolve"
                }
            ])
        
        else:
            return f"This is placeholder content for {prompt_type} in development mode."


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider integration.
    
    TODO: Add support for Claude streaming and model selection.
    """
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model: str = "claude-3-opus-20240229",
                 temperature: float = 0.7,
                 **kwargs):
        """Initialize the Anthropic provider.
        
        Args:
            api_key: Anthropic API key.
            model: Model to use for content generation.
            temperature: Controls randomness in output.
            **kwargs: Additional provider-specific parameters.
        """
        super().__init__(api_key, **kwargs)
        self.model = model
        self.temperature = temperature
        self.api_url = "https://api.anthropic.com/v1/messages"
        
    def generate_content(self, prompt: str, prompt_type: str = "script", **kwargs) -> str:
        """Generate content using the Anthropic API.
        
        Args:
            prompt: The prompt to send to the API.
            prompt_type: Type of prompt (for mock responses).
            **kwargs: Additional parameters.
            
        Returns:
            Generated content as text.
        """
        import hashlib
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        # Check for mock response in dev mode
        mock_response = self.get_mock_response(prompt_hash, prompt_type)
        if mock_response:
            logger.info(f"Using mock response for {prompt_type}")
            return mock_response
            
        if self.is_dev_mode:
            # Generate placeholder content in dev mode
            logger.info(f"DEV MODE: Would call Anthropic API with prompt: {prompt[:100]}...")
            mock_content = self._generate_placeholder_content(prompt, prompt_type)
            self.save_mock_response(prompt, mock_content, prompt_type)
            return mock_content
            
        # Real API call for production
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": 4000,
            **kwargs
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            content = response.json()["content"][0]["text"]
            self.save_mock_response(prompt, content, prompt_type)
            return content
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}")
            return self._generate_placeholder_content(prompt, prompt_type)
            
    def _generate_placeholder_content(self, prompt: str, prompt_type: str) -> str:
        """Generate placeholder content for development mode."""
        if prompt_type == "script":
            return """Scene 1: Opening Hook
[Aerial view of busy digital network visualization]
In a world where data never sleeps, automation has become the backbone of efficient business operations.

Scene 2: Problem Statement
[Split screen showing manual vs automated workflow]
Traditional methods require countless hours of manual intervention, creating bottlenecks and introducing human error.

Scene 3: Solution Introduction
[Clean visualization of the automation platform interface]
Our multi-niche automation platform bridges these gaps, creating seamless workflows across your entire organization.

Scene 4: Feature Highlight - Content Creation
[Show content being automatically generated]
Automatically generate context-aware content tailored to your specific industry needs.

Scene 5: Feature Highlight - Media Processing
[Show video and images being processed]
Transform raw media into polished, professional assets with minimal human intervention.

Scene 6: Real-world Application
[Case study visualization with metrics]
Companies implementing our solution have seen productivity increases of up to 67% in the first quarter alone.

Scene 7: Call to Action
[Clean screen with logo and contact information]
Discover how our automation platform can revolutionize your workflow. Contact us today for a personalized demonstration."""
        else:
            return f"This is placeholder content for {prompt_type} in development mode."


class StabilityAIProvider(AIProvider):
    """Stability AI provider for image generation.
    
    TODO: Add error handling for image generation failures and support for more engines.
    """
    def __init__(self, 
                 api_key: Optional[str] = None,
                 engine: str = "stable-diffusion-xl-1024-v1-0",
                 **kwargs):
        """Initialize the Stability AI provider.
        
        Args:
            api_key: Stability AI API key.
            engine: Model engine to use.
            **kwargs: Additional provider-specific parameters.
        """
        super().__init__(api_key, **kwargs)
        self.engine = engine
        self.api_url = f"https://api.stability.ai/v1/generation/{self.engine}/text-to-image"
        
    def generate_image(self, prompt: str, output_path: Optional[str] = None, **kwargs) -> Union[str, bytes]:
        """Generate an image using the Stability AI API.
        
        Args:
            prompt: The image description prompt.
            output_path: Path to save the generated image.
            **kwargs: Additional parameters.
            
        Returns:
            Path to the generated image or image data.
        """
        import hashlib
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        
        # Check for mock response in dev mode
        mock_file = self.mock_responses_dir / f"image_{prompt_hash}.png"
        if self.is_dev_mode and mock_file.exists():
            logger.info(f"Using mock image for prompt: {prompt[:50]}...")
            if output_path:
                import shutil
                shutil.copy(mock_file, output_path)
                return output_path
            else:
                with open(mock_file, 'rb') as f:
                    return f.read()
        
        if self.is_dev_mode:
            # In dev mode, use a placeholder image
            logger.info(f"DEV MODE: Would generate image for prompt: {prompt[:50]}...")
            
            # Generate a simple colored rectangle with PIL
            from PIL import Image, ImageDraw, ImageFont
            import random
            
            # Create a random colored image
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            img = Image.new('RGB', (1024, 1024), color=color)
            draw = ImageDraw.Draw(img)
            
            # Add text with the prompt
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except IOError:
                font = ImageFont.load_default()
                
            # Wrap text to fit image width
            import textwrap
            lines = textwrap.wrap(f"DEV MODE: {prompt}", width=40)
            y_position = 50
            for line in lines:
                draw.text((50, y_position), line, fill=(255, 255, 255), font=font)
                y_position += 30
                
            # Save the image
            if not output_path:
                output_path = str(self.mock_responses_dir / f"image_{prompt_hash}.png")
                
            img.save(output_path)
            return output_path
            
        # Real API call for production
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 30,
            **kwargs
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            
            # Get the image data
            image_data = response.json()["artifacts"][0]["base64"]
            import base64
            image_bytes = base64.b64decode(image_data)
            
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(image_bytes)
                return output_path
            else:
                return image_bytes
                
        except Exception as e:
            logger.error(f"Error calling Stability AI API: {e}")
            # Fall back to placeholder in case of error
            return self.generate_image(prompt, output_path, dev_mode=True)


class ContentAPIHub:
    """Hub for managing different AI content generation APIs.
    
    TODO: Add provider prioritization, fallback logic, and advanced logging.
    """
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the Content API Hub.
        
        Args:
            config: Configuration dictionary.
        """
        self.config = config or {}
        self.providers = {}
        self._init_providers()
        
    def _init_providers(self):
        """Initialize available AI providers based on configuration."""
        # Text generation providers
        self.providers["openai"] = OpenAIProvider(
            model=self.config.get("openai", {}).get("model", "gpt-4-turbo-preview"),
            temperature=self.config.get("openai", {}).get("temperature", 0.7)
        )
        
        self.providers["anthropic"] = AnthropicProvider(
            model=self.config.get("anthropic", {}).get("model", "claude-3-opus-20240229"),
            temperature=self.config.get("anthropic", {}).get("temperature", 0.7)
        )
        
        # Image generation providers
        self.providers["stability"] = StabilityAIProvider(
            engine=self.config.get("stability", {}).get("engine", "stable-diffusion-xl-1024-v1-0")
        )
    
    def set_api_key(self, provider_name: str, api_key: str) -> bool:
        """Set or update API key for a specific provider.
        
        Args:
            provider_name: Name of the provider.
            api_key: API key to set.
            
        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            provider_name = provider_name.lower()
            
            # Create provider if it doesn't exist
            if provider_name not in self.providers:
                if provider_name == "openai":
                    self.providers[provider_name] = OpenAIProvider(api_key=api_key)
                elif provider_name == "anthropic":
                    self.providers[provider_name] = AnthropicProvider(api_key=api_key)
                elif provider_name == "stability":
                    self.providers[provider_name] = StabilityAIProvider(api_key=api_key)
                else:
                    logger.warning(f"Unknown provider {provider_name}")
                    return False
            else:
                # Update existing provider's API key
                provider = self.providers[provider_name]
                provider.api_key = api_key
                
                # Special handling for OpenAI which needs global API key setting
                if provider_name == "openai":
                    import openai
                    openai.api_key = api_key
                
            logger.info(f"API key updated for {provider_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting API key for {provider_name}: {e}")
            return False
        
    def get_provider(self, provider_name: str) -> AIProvider:
        """Get AI provider by name.
        
        Args:
            provider_name: Name of the provider.
            
        Returns:
            AIProvider instance.
            
        Raises:
            ValueError: If provider is not found.
        """
        provider = self.providers.get(provider_name.lower())
        if not provider:
            raise ValueError(f"Provider {provider_name} not found")
        return provider
        
    def generate_content(self, 
                         prompt: str, 
                         provider: str = "openai", 
                         content_type: str = "script",
                         **kwargs) -> str:
        """Generate content using specified provider.
        
        Args:
            prompt: Content generation prompt.
            provider: Provider name.
            content_type: Type of content to generate.
            **kwargs: Additional parameters to pass to the provider.
            
        Returns:
            Generated content.
        """
        provider_instance = self.get_provider(provider)
        return provider_instance.generate_content(prompt, prompt_type=content_type, **kwargs)
        
    def generate_image(self,
                       prompt: str,
                       provider: str = "stability",
                       output_path: Optional[str] = None,
                       **kwargs) -> Union[str, bytes]:
        """Generate image using specified provider.
        
        Args:
            prompt: Image generation prompt.
            provider: Provider name.
            output_path: Path to save the generated image.
            **kwargs: Additional parameters to pass to the provider.
            
        Returns:
            Path to generated image or image data.
        """
        provider_instance = self.get_provider(provider)
        if not hasattr(provider_instance, "generate_image"):
            raise ValueError(f"Provider {provider} does not support image generation")
            
        return provider_instance.generate_image(prompt, output_path, **kwargs)


# Factory function to create ContentAPIHub instance
def create_api_hub(config: Optional[Dict] = None) -> ContentAPIHub:
    """Create a ContentAPIHub instance.
    
    Args:
        config: Configuration dictionary.
        
    Returns:
        ContentAPIHub instance.
    """
    return ContentAPIHub(config)

# TODO: Add integration tests for all AI providers and the ContentAPIHub factory.
