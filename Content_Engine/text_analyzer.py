def extract_keywords(script_text: str) -> list:
    """
    Extracts keywords from the script text.
    (Placeholder implementation: returns the first five words as keywords.)
    """
    words = script_text.split()
    keywords = words[:5]
    return keywords

if __name__ == "__main__":
    sample = "This is a test script for keyword extraction in our project."
    print("Extracted Keywords:", extract_keywords(sample))
