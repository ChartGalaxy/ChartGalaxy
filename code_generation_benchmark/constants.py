from configs.loader import load_config
from configs.loader import load_env
from pathlib import Path

APIS = load_env()

_cfg = load_config()

MODEL_TYPES = _cfg["models"]
VLM_PARAMS = _cfg["VLM"]

HIGH_LEVEL_EVAL_PROMPT_FILE = Path('./prompts') / _cfg["prompts"]["high_level_eval_prompt_file"]
CHAT_PROMPT_FILE = Path('./prompts') / _cfg["prompts"]["chat_prompt_file"]
EVAL_MODEL = _cfg["eval_model"]

ROOT_DIR = Path(_cfg["dirs"]["data_root_dir"])
OUTPUT_DIR = Path(_cfg["dirs"]["output_dir"])
LOG_DIR = Path(_cfg["dirs"]["log_dir"])

LOG_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_WORKERS = _cfg["n_workers"]
CLIP_CACHE_DIR = _cfg["dirs"]["clip_cache_dir"]
