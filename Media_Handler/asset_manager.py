import os

def get_asset(asset_name: str, asset_folder: str = "./Content_Engine/assets") -> str:
    """
    Retrieve the full path for a given asset.
    Raises FileNotFoundError if the asset does not exist.
    """
    asset_path = os.path.join(asset_folder, asset_name)
    if os.path.exists(asset_path):
        return asset_path
    else:
        raise FileNotFoundError(f"Asset '{asset_name}' not found in {asset_folder}")

if __name__ == "__main__":
    try:
        print("Asset path:", get_asset("example_image.jpg"))
    except FileNotFoundError as e:
        print(e)
