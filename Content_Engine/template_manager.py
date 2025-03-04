def get_default_template() -> dict:
    """
    Returns a default template configuration.
    This includes style, font, color, background, and transition settings.
    """
    template = {
        "style": "default",
        "font": "Arial",
        "color": "#FFFFFF",
        "background": "#000000",
        "transitions": {
            "type": "fade",
            "duration": 2  # seconds
        }
    }
    return template

if __name__ == "__main__":
    print("Default Template:", get_default_template())
