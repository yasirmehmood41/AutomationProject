import yaml
import os

def load_config(config_file=None):
    # Determine the project root (assumes this file is in the 'utils' folder)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if config_file is None:
        config_file = os.path.join(base_dir, "config.yaml")
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"{config_file} not found!")
    with open(config_file, "r") as f:
        return yaml.safe_load(f)

# Example usage:
if __name__ == "__main__":
    config = load_config()
    print(config)
