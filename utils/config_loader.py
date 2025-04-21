import yaml
import os
import logging

def load_config(config_file=None):
    """
    Load YAML configuration file from project root.
    Args:
        config_file: Optional path to config file. Defaults to project root config.yaml.
    Returns:
        Parsed config as a dictionary.
    Raises:
        FileNotFoundError: If config file is missing.
        yaml.YAMLError: If YAML is invalid.
    """
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if config_file is None:
        config_file = os.path.join(base_dir, "config.yaml")
    if not os.path.exists(config_file):
        logging.error(f"Config file not found: {config_file}")
        raise FileNotFoundError(f"{config_file} not found!")
    try:
        with open(config_file, "r") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        logging.error(f"Error loading YAML config: {e}")
        raise

# Example usage:
if __name__ == "__main__":
    config = load_config()
    print(config)
