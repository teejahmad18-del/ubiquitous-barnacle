import os
from django.http import HttpResponse, JsonResponse
import threading
import time
import importlib
import sys
from io import StringIO

# Persistent storage files
STATE_FILE = os.path.join(os.path.dirname(__file__), 'bot_state.json')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), 'bot_output.txt')

# Initialize bot state
bot_state = {
    "is_running": False,
    "last_run": None,
    "output": "",
    "status": "idle",
    "execution_time": 0
}

def _load_state():
    """Load persisted state from file"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return eval(f.read())
        except:
            pass
    return bot_state

def _save_state():
    """Save current state to file"""
    with open(STATE_FILE, 'w') as f:
        f.write(str(bot_state))

def _save_output(content):
    """Save output to persistent file"""
    with open(OUTPUT_FILE, 'w') as f:
        f.write(content)

def _load_output():
    """Load output from persistent file"""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r') as f:
            return f.read()
    return "No output available yet"

# Load initial state
bot_state.update(_load_state())
bot_state['output'] = _load_output()

def trigger_bot(request):
    if bot_state["is_running"]:
        return HttpResponse(
            f"Bot is already running\n\nLast output:\n{bot_state['output']}",
            content_type="text/plain"
        )
    
    # Setup output capture
    output_buffer = StringIO()
    sys.stdout = output_buffer
    sys.stderr = output_buffer
    
    def run_script():
        global bot_state
        start_time = time.time()
        
        try:
            # Initialize state
            bot_state.update({
                "is_running": True,
                "status": "running",
                "output": "",
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            _save_state()
            
            # Execute trading script
            trading = importlib.import_module('trading.trading_logic')
            
            if hasattr(trading, '__main__'):
                trading.__main__()
            else:
                with open(os.path.join(os.path.dirname(__file__), 'trading_logic.py'), 'r') as f:
                    exec(f.read(), {'__name__': '__main__'})
            
            bot_state["status"] = "completed"
            
        except Exception as e:
            bot_state["status"] = f"error: {str(e)}"
            print(f"ERROR: {str(e)}")
            
        finally:
            # Capture and save all output
            output_content = output_buffer.getvalue()
            _save_output(output_content)
            
            bot_state.update({
                "is_running": False,
                "last_run": time.strftime("%Y-%m-%d %H:%M:%S"),
                "output": output_content,
                "execution_time": round(time.time() - start_time, 2)
            })
            _save_state()
            
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
    
    # Start execution thread
    thread = threading.Thread(target=run_script)
    thread.daemon = True
    thread.start()
    
    return HttpResponse(
        "Trading bot started successfully\nRefresh /output/ to see results",
        content_type="text/plain"
    )

def get_output(request):  # Changed from bot_output to get_output
    """View the current output (renamed to match import)"""
    current_output = _load_output()
    
    response = (
        f"Status: {bot_state['status']}\n"
        f"Last run: {bot_state['last_run'] or 'Never'}\n"
        f"Running: {bot_state['is_running']}\n"
        f"Execution time: {bot_state.get('execution_time', 0)}s\n\n"
        f"Output:\n{current_output}"
    )
    return HttpResponse(response, content_type="text/plain")

def bot_status(request):
    return JsonResponse(bot_state)