import re
import os

content = "poll_seconds: ${POLL_SECONDS}"

def replace_env_vars(match):
    var_name = match.group(1)
    value = os.getenv(var_name, "60")  # Default to "60" if env var is missing
    print(f"[DEBUG] Substituting placeholder '{var_name}' with value '{value}'.")
    return value

content = re.sub(r'\$\{([^}]+)\}', replace_env_vars, content)
print("[DEBUG] Final content:")
print(content)