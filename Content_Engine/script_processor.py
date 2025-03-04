def process_script(script_text: str) -> list:
    # Placeholder: Split script into scenes
    scenes = script_text.split("\n\n")
    return scenes

if __name__ == "__main__":
    sample = "Scene 1: Hello.\n\nScene 2: World."
    print(process_script(sample))
