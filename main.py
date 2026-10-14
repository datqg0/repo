# main.py - Root entry point for JobHunter Bot
import sys
from pathlib import Path

# Thêm thư mục src vào sys.path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Ủy quyền thực thi cho src/main.py
if __name__ == "__main__":
    from src.main import main, __name__ as main_name
    import runpy
    runpy.run_path(str(SRC_DIR / "main.py"), run_name="__main__")
