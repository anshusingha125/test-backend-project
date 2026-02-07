import json
import os
import re

# STATE_FILE = "state.json"


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(BASE_DIR, "state.json")


def load_state():
    """Loads the application state from state.json."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_state(state):
    """Saves the application state to state.json."""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def parse_llm_output(llm_output):
    """
    Parses the LLM output to extract the plan.
    Expected output from LLM should be a JSON block.
    
    Returns:
        dict: The parsed plan containing 'total_phases' and 'phases' list.
              Returns None if parsing fails.
    """
    # Try to find JSON block in markdown code fences
    json_match = re.search(r'```json\s*(.*?)\s*```', llm_output, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find the first '{' and last '}'
        start_idx = llm_output.find('{')
        end_idx = llm_output.rfind('}')
        if start_idx != -1 and end_idx != -1:
            json_str = llm_output[start_idx:end_idx+1]
        else:
            return None

    try:
        plan = json.loads(json_str)
        # Basic validation
        if "total_phases" in plan and "phases" in plan:
            return plan
        return None
    except json.JSONDecodeError:
        return None
