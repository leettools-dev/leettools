from pathlib import Path

# Get the eval directory path
EVAL_DIR = Path(__file__).parent.parent
DEFAULT_FINANCEBENCH_PATH = EVAL_DIR / "data" / "financebench" 
DEFAULT_MEDICALBENCH_PATH = EVAL_DIR / "data" / "medicalbench"