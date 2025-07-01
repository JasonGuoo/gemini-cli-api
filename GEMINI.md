The project goal is to expose the gemini-cli as a RESTful API compatible with the OpenAI API.
1. Be a stateless server.
2. No backend sub-processes as the server, using `gemini --prompt` instead.
3. Don't provide API key management.
4. Using FastAPI
5. Support stream as well.
