def generate_scene_metadata(script_text: str) -> list:
    """
    Generates metadata for each scene by splitting the script and assigning default durations.
    Returns a list of dictionaries with scene number, text, and duration.
    """
    scenes = script_text.split("\n\n")
    metadata = []
    for i, scene in enumerate(scenes, start=1):
        # Simple heuristic: duration is the maximum of 5 seconds or based on text length
        duration = max(5, len(scene) // 10)
        metadata.append({
            "scene_number": i,
            "text": scene,
            "duration": duration
        })
    return metadata

if __name__ == "__main__":
    sample = "Scene 1: Hello.\n\nScene 2: World."
    print("Scene Metadata:", generate_scene_metadata(sample))
