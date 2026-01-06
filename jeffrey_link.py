#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
JEFFREY NEURAL LINK v2.0 (AUTO)
PAC-20260106-TOOLING-NEURAL-LINK
═══════════════════════════════════════════════════════════════════════════════
CLI bridge to Gemini API for Constitutional PAC generation.
Auto-selects best available model with rate limit handling.

Author: ATLAS (GID-11) — Repository Integrity Engineer
Issuer: JEFFREY (GID-00) — Orchestrator
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import time
import google.generativeai as genai
from google.api_core import exceptions

# --- CONFIGURATION ---
# Priority List: Try these models in order.
MODEL_PRIORITY = [
    'gemini-1.5-pro-latest',  # Smartest Stable
    'gemini-pro-latest',      # Fallback Smart
    'gemini-2.5-flash',       # New Speedster (High Limit)
    'gemini-flash-latest',    # Old Reliable
]

def get_api_key():
    key = os.environ.get("JEFFREY_API_KEY")
    if not key:
        print("❌ ERROR: JEFFREY_API_KEY is missing.")
        exit(1)
    return key

def connect_brain():
    genai.configure(api_key=get_api_key())
    
    print("📡 SCANNING ORBITAL TARGETS...")
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name.replace('models/', ''))
    except Exception as e:
        print(f"⚠️  Radar malfunction: {e}")

    # Select the best available model
    selected_model = None
    for priority in MODEL_PRIORITY:
        if priority in available_models:
            selected_model = priority
            break
            
    # Fallback if exact match fails, use the first priority that might work
    if not selected_model:
        selected_model = MODEL_PRIORITY[0] 

    print(f"🔗 LOCKED ON: {selected_model}")
    return genai.GenerativeModel(selected_model)

def generate_pac(model, prompt):
    print("⚡ COMMUNICATING WITH ORCHESTRATOR...")
    retries = 3
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except exceptions.ResourceExhausted as e:
            wait_time = 35  # Standard Google cooldown is ~30s
            print(f"🛑 RATE LIMIT HIT. Cooling down for {wait_time}s... (Attempt {attempt+1}/{retries})")
            time.sleep(wait_time)
            print("🔄 RETRYING...")
        except Exception as e:
            print(f"❌ CRITICAL ERROR: {e}")
            return None
    print("💀 ORCHESTRATOR UNRESPONSIVE. Try again later.")
    return None

# --- MAIN LOOP ---
if __name__ == "__main__":
    print("\n╔════════════════════════════════════════════╗")
    print("║      JEFFREY NEURAL LINK v2.0 (AUTO)       ║")
    print("╚════════════════════════════════════════════╝\n")
    
    model = connect_brain()
    
    while True:
        target = input("\n🎯 ENTER TARGET (or 'exit'): ")
        if target.lower() in ['exit', 'quit']:
            break
            
        result = generate_pac(model, target)
        
        if result:
            with open("PAC_INBOX.yaml", "w") as f:
                f.write(result)
            print(f"\n✅ PAC GENERATED: PAC_INBOX.yaml")
