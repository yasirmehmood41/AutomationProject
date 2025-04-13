"""Video transition effects module."""
from typing import Dict, Optional
from moviepy.editor import VideoFileClip, CompositeVideoClip, concatenate_videoclips
from moviepy.video import fx as vfx
import numpy as np

class TransitionEffect:
    """Base class for transition effects."""
    def __init__(self, duration: float = 1.0):
        self.duration = duration

    def __call__(self, clip1: VideoFileClip, clip2: VideoFileClip) -> VideoFileClip:
        """Apply transition effect between two clips."""
        # Ensure clips have proper duration
        clip1 = clip1.set_duration(clip1.duration)
        clip2 = clip2.set_duration(clip2.duration)
        
        # Create transition clip
        transition = CompositeVideoClip([
            clip1.set_end(clip1.duration - self.duration/2),
            clip2.set_start(-self.duration/2)
        ])
        return transition

class FadeTransition(TransitionEffect):
    """Simple fade transition between clips."""
    def __call__(self, clip1: VideoFileClip, clip2: VideoFileClip) -> VideoFileClip:
        clip1 = clip1.crossfadein(self.duration)
        clip2 = clip2.crossfadeout(self.duration)
        return concatenate_videoclips([clip1, clip2])

class SlideTransition(TransitionEffect):
    """Slide one clip over another."""
    def __init__(self, duration: float = 1.0, direction: str = "left"):
        super().__init__(duration)
        self.direction = direction

    def __call__(self, clip1: VideoFileClip, clip2: VideoFileClip) -> VideoFileClip:
        w, h = clip1.size
        direction = self.direction.lower()
        
        def slide(t):
            progress = t / self.duration
            if direction == "left":
                return {'x': int(w * (1-progress))}
            elif direction == "right":
                return {'x': int(-w * (1-progress))}
            elif direction == "up":
                return {'y': int(h * (1-progress))}
            else:  # down
                return {'y': int(-h * (1-progress))}
        
        sliding = clip2.set_position(slide)
        return CompositeVideoClip([clip1, sliding])

class TransitionManager:
    """Manages video transitions."""
    def __init__(self):
        self.transitions = {
            "fade": {
                "name": "Fade",
                "description": "Smooth fade transition between scenes",
                "duration": 0.5,
                "effect": FadeTransition
            },
            "slide": {
                "name": "Slide",
                "description": "Slide scenes horizontally",
                "duration": 0.7,
                "effect": SlideTransition
            }
        }
    
    def get_available_transitions(self) -> Dict:
        """Get available transition effects."""
        return self.transitions
    
    def create_transition(self, clip1: VideoFileClip, clip2: VideoFileClip, duration: float = 0.5, type: str = "fade") -> Optional[VideoFileClip]:
        """Create a transition between two video clips."""
        try:
            if type not in self.transitions:
                print(f"Warning: Unknown transition type '{type}', falling back to fade")
                type = "fade"
            
            transition_class = self.transitions[type]["effect"]
            transition = transition_class(duration=duration)
            return transition(clip1, clip2)
        except Exception as e:
            print(f"Error creating transition: {str(e)}")
            return None

    def apply_transition(
        self,
        clip1: VideoFileClip,
        clip2: VideoFileClip,
        transition_type: str = "fade",
        duration: Optional[float] = None
    ) -> VideoFileClip:
        """Apply transition effect between two clips."""
        if transition_type not in self.transitions:
            print(f"Unknown transition {transition_type}. Using fade.")
            transition_type = "fade"
        
        if not duration:
            duration = self.transitions[transition_type]["duration"]
        
        try:
            transition_class = self.transitions[transition_type]["effect"]
            transition = transition_class(duration=duration)
            return transition(clip1, clip2)
        except Exception as e:
            print(f"Error applying transition: {str(e)}")
            return clip1

if __name__ == "__main__":
    # Example usage
    manager = TransitionManager()
    
    # List available transitions
    print("Available transitions:", manager.get_available_transitions())
    
    # Preview a transition
    preview = manager.get_available_transitions()
    print("\nTransition Preview:", preview)
