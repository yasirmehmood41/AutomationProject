import os
import logging

def get_asset(asset_name: str, asset_folder: str = "./Content_Engine/assets") -> str:
    """
    Retrieve the full path for a given asset.
    Args:
        asset_name: Name of the asset file.
        asset_folder: Folder where assets are stored.
    Returns:
        Full path to asset if it exists, else None.
    Logs a warning if the asset does not exist.
    TODO: Add support for asset validation, allowed extensions, and fallback assets.
    """
    asset_path = os.path.join(asset_folder, asset_name)
    if os.path.exists(asset_path):
        return asset_path
    else:
        logging.warning(f"Asset '{asset_name}' not found in {asset_folder}")
        return None

if __name__ == "__main__":
    try:
        print("Asset path:", get_asset("example_image.jpg"))
    except Exception as e:
        print(e)
