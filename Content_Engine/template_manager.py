from typing import Dict, Optional
import yaml

class TemplateManager:
    def __init__(self):
        self.templates = {
            "educational": {
                "style": "professional",
                "font": "Roboto",
                "color_scheme": {
                    "primary": "#2C3E50",
                    "secondary": "#ECF0F1",
                    "accent": "#3498DB"
                },
                "transitions": {
                    "type": "smooth",
                    "duration": 1.5
                },
                "pacing": "moderate",
                "effects": ["text_highlight", "zoom_focus"]
            },
            "entertainment": {
                "style": "dynamic",
                "font": "Montserrat",
                "color_scheme": {
                    "primary": "#E74C3C",
                    "secondary": "#F1C40F",
                    "accent": "#9B59B6"
                },
                "transitions": {
                    "type": "energetic",
                    "duration": 0.8
                },
                "pacing": "fast",
                "effects": ["shake", "flash", "pop"]
            },
            "business": {
                "style": "corporate",
                "font": "Open Sans",
                "color_scheme": {
                    "primary": "#34495E",
                    "secondary": "#BDC3C7",
                    "accent": "#2980B9"
                },
                "transitions": {
                    "type": "clean",
                    "duration": 1.2
                },
                "pacing": "slow",
                "effects": ["fade", "slide"]
            },
            "lifestyle": {
                "style": "casual",
                "font": "Lato",
                "color_scheme": {
                    "primary": "#16A085",
                    "secondary": "#F5F5F5",
                    "accent": "#E67E22"
                },
                "transitions": {
                    "type": "smooth",
                    "duration": 1.0
                },
                "pacing": "natural",
                "effects": ["blur", "overlay"]
            }
        }

    def get_template(self, niche: str = "educational", style_override: Optional[Dict] = None) -> dict:
        """
        Get a template configuration for a specific niche.
        
        Args:
            niche (str): The content niche (educational, entertainment, business, lifestyle)
            style_override (dict, optional): Override specific style settings
            
        Returns:
            dict: Template configuration
        """
        template = self.templates.get(niche.lower(), self.templates["educational"]).copy()
        
        if style_override:
            template.update(style_override)
            
        return template

    def add_custom_template(self, niche: str, template_config: Dict):
        """
        Add a custom template for a specific niche.
        
        Args:
            niche (str): The content niche name
            template_config (dict): Template configuration
        """
        self.templates[niche.lower()] = template_config

    def get_available_niches(self) -> list:
        """
        Get list of available template niches.
        
        Returns:
            list: Available niches
        """
        return list(self.templates.keys())

def get_default_template(niche: str = "educational") -> dict:
    """
    Returns a template configuration for the specified niche.
    This includes style, font, color scheme, and transition settings.
    """
    template_manager = TemplateManager()
    return template_manager.get_template(niche)

if __name__ == "__main__":
    tm = TemplateManager()
    print("Available niches:", tm.get_available_niches())
    print("\nEducational Template:", tm.get_template("educational"))
    print("\nEntertainment Template:", tm.get_template("entertainment"))
