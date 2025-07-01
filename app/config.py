import shutil
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Find the path to the gemini executable
GEMINI_CLI_PATH = shutil.which("gemini")

# Validate that the executable was found
if not GEMINI_CLI_PATH:
    raise FileNotFoundError(
        "Error: 'gemini' executable not found in your system's PATH. "
        "Please ensure the gemini-cli tool is installed and accessible."
    )



# Debugging feature configuration
DEBUG_DUMP_ENABLED = os.getenv("DEBUG_DUMP_ENABLED", "False").lower() == "true"
DEBUG_DUMP_DIR = os.getenv("DEBUG_DUMP_DIR", "./debug_dumps")

# Console output configuration
CONSOLE_OUTPUT_ENABLED = os.getenv("CONSOLE_OUTPUT_ENABLED", "True").lower() == "true"
CONSOLE_OUTPUT_VERBOSE = os.getenv("CONSOLE_OUTPUT_VERBOSE", "True").lower() == "true"

# Ensure the debug dump directory exists if debugging is enabled
if DEBUG_DUMP_ENABLED and not os.path.exists(DEBUG_DUMP_DIR):
    os.makedirs(DEBUG_DUMP_DIR)