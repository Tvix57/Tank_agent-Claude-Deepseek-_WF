#!/usr/bin/env python3
"""UserPromptSubmit-хук: если почасовая проверка токенов была снята из-за простоя (маркер от
token_usage_check.py), напомнить пересоздать её и удалить маркер."""

import json
import os
import sys

PAUSE_DIR = os.path.expanduser("~/.claude/token_check_paused")

try:
    session_id = json.load(sys.stdin).get("session_id") or ""
except (json.JSONDecodeError, AttributeError):
    sys.exit(0)

marker = os.path.join(PAUSE_DIR, session_id)
if session_id and os.path.isfile(marker):
    os.remove(marker)
    print("Почасовая проверка токенов была снята из-за простоя сессии. Пользователь вернулся — "
          "пересоздай её по CLAUDE.md, раздел «Контроль расхода токенов» (сначала сверь CronList).")
