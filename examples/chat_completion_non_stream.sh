#!/bin/bash

curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{ "model": "gemini-2.5-flash", "messages": [{"role": "user", "content": "Hello, how are you today?"}], "stream": false }'