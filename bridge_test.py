"""
CHAINBRIDGE PROBE - P09
Atomic Unit: Proof -> Decision -> Outcome
"""
import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv

# 1. PROOF OF ENVIRONMENT
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("🔴 FAILURE: GOOGLE_API_KEY missing in .env")
    sys.exit(1)

# 2. DECISION (CONFIGURE)
try:
    genai.configure(api_key=api_key)
    # Using 'gemini-2.0-flash' (current production model)
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    print(f"🔴 CONFIG ERROR: {e}")
    sys.exit(1)

# 3. OUTCOME (EXECUTE)
print("🔵 SENDING PROBE...")
try:
    response = model.generate_content("Confirm Benson Execution status: ONLINE.")
    
    if response.text:
        print("\n" + "="*40)
        print("🟢 SUCCESS: CONNECTION ESTABLISHED")
        print(f"Server Response: {response.text.strip()}")
        print("="*40)
    else:
        print("🔴 FAILURE: Empty response.")

except Exception as e:
    print(f"\n🔴 EXECUTION ERROR: {e}")
    sys.exit(1)
