#!/bin/bash

curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{ "model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "Tell me a short story about a brave knight and a dragon." }], "stream": true }'