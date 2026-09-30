import sys
from pathlib import Path


_generated_path = Path(__file__).parent / "generated"

if str(_generated_path) not in sys.path:
    sys.path.insert(0, str(_generated_path))