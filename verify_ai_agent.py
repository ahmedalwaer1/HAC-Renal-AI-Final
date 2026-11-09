"""Verify AI Agent is calling Python tools (not hallucinating)."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agents.llm_agent import create_agent_executor

# Test 1: Verify API Key is loaded
api_key = os.getenv("LLM_API_KEY")
print(f"API Key loaded: {'YES' if api_key and api_key != 'your_api_key_here' else 'NO - USING PLACEHOLDER'}")

# Test 2: Run a simple query through the AI Agent
patient_query = """
Patient needs Meropenem dosing.
Age: 65, Weight: 75kg, CrCl: 18 mL/min, No dialysis, Standard indication, Short infusion.
Calculate the dose using the provided tools.
"""

try:
    agent_executor = create_agent_executor()
    result = agent_executor.invoke({"input": patient_query})
    print("\n=== AI Agent Response ===")
    print(result['output'])
    
    # Check if the agent actually called the tools
    intermediate = result.get('intermediate_steps', [])
    steps_str = str(intermediate)
    if "get_meropenem_dose" in steps_str:
        print("\n✅ SUCCESS: Agent called the Python tool (get_meropenem_dose)")
    else:
        print("\n❌ FAILURE: Agent did NOT call the Python tool - it may be hallucinating!")
        print("Intermediate steps available:", intermediate)
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("The AI Agent is not working correctly.")