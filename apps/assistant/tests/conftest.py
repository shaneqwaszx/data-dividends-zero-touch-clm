"""Disable owner dotenv/model configuration before Copilot test-module composition."""

import os

from copilot.config import CopilotSettings

CopilotSettings.model_config = {**CopilotSettings.model_config, "env_file": None}
os.environ["COPILOT_LLM_ENABLED"] = "false"
os.environ["COPILOT_CLM_BACKEND_URL"] = "http://127.0.0.1:1"
