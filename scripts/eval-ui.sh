#!/bin/bash
# Start the Ragbits Eval UI with both frontend and backend in kitty split panes
# Usage: ./scripts/eval-ui.sh
# If already running, kills existing processes and restarts them

RAGBITS_ROOT="/home/mateusz/workspace/oss/ragbits"

# Kill existing processes if running
BACKEND_PID=$(pgrep -f "run_eval_ui.py")
FRONTEND_PID=$(pgrep -f "vite.*eval")

if [[ -n "$BACKEND_PID" || -n "$FRONTEND_PID" ]]; then
    echo "Stopping existing processes..."
    [[ -n "$BACKEND_PID" ]] && kill $BACKEND_PID 2>/dev/null && echo "  Killed backend (PID: $BACKEND_PID)"
    [[ -n "$FRONTEND_PID" ]] && kill $FRONTEND_PID 2>/dev/null && echo "  Killed frontend (PID: $FRONTEND_PID)"
    sleep 1
fi

# Launch backend in a new vertical split pane (pass OPENAI_API_KEY to the subprocess)
kitten @ launch --location=vsplit --cwd="$RAGBITS_ROOT" --title="Eval Backend" --env="OPENAI_API_KEY=$OPENAI_API_KEY" bash -c "cd $RAGBITS_ROOT && uv run python examples/evaluate/agent-scenarios/run_eval_ui.py; exec bash"

# Run frontend in current pane
cd "$RAGBITS_ROOT/typescript/ui" && npm run dev:eval
