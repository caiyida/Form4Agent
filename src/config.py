from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 各个文件夹
TEMPLATE_DIR = PROJECT_ROOT / "templates"
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"

# 文件路径
FORM4_TEMPLATE = TEMPLATE_DIR / "Form4_Template.docx"
FORM_DATA_FILE = INPUT_DIR / "form_data.json"
SAMPLE_PASSPORT_FILE = INPUT_DIR / "passport.jpg"