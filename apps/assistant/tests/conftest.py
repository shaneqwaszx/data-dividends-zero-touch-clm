"""Disable owner dotenv/model configuration before AI Assistant test-module composition."""

import os

from ai_assistant.config import AiAssistantSettings

AiAssistantSettings.model_config = {**AiAssistantSettings.model_config, "env_file": None}
os.environ["AI_ASSISTANT_LLM_ENABLED"] = "false"
os.environ["AI_ASSISTANT_CLM_BACKEND_URL"] = "http://127.0.0.1:1"
