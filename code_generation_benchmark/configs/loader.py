import yaml
from pathlib import Path
import os
from dotenv import load_dotenv
from pathlib import Path


def load_config(path: str = "configs/default_config.yaml") -> dict:
    with open(Path(path), "r") as f:
        config = yaml.safe_load(f)
    return config


def load_env() -> dict:
    env_path = Path('.') / 'configs' / '.env'
    load_dotenv(dotenv_path=env_path)
    env_dict = {}
    for name in ['OPENAI', 'GEMINI', 'CLAUDE', 'INTERN']:
        env_dict[name.lower()] = {
            "API_KEY": os.getenv(f"EVAL_API_KEY_{name}", "xxx"),
            "BASE_URL": os.getenv(f"EVAL_BASE_URL_{name}", "xxx"),
        }
    return env_dict
