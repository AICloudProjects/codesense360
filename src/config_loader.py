import os
import yaml
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def load_config(path="config/config.yaml"):
    """Load YAML config and substitute environment variables."""
    with open(path, "r") as file:
        config = yaml.safe_load(file)
    
    # Replace ${VAR} placeholders
    def replace_env_vars(obj):
        if isinstance(obj, dict):
            return {k: replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_env_vars(i) for i in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            return os.getenv(obj[2:-1], obj)
        else:
            return obj

    return replace_env_vars(config)

if __name__ == "__main__":
    config = load_config()
    print(config)