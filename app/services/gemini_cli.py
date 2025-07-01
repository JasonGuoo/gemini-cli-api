import asyncio
import os
import codecs
import re
from typing import AsyncGenerator, Tuple
from app.config import GEMINI_CLI_PATH

async def execute_gemini_command(prompt: str, model_name: str | None = None, stream: bool = False) -> AsyncGenerator[Tuple[str, str], None]:
    """
    Executes the gemini CLI with a given prompt and streams the output.
    """
    cmd = [GEMINI_CLI_PATH]
    if model_name:
        cmd.extend(["--model", model_name])
    cmd.extend(["--prompt", prompt])

    # Pass the current environment variables to the subprocess
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ
    )

    if stream:
        decoder = codecs.getincrementaldecoder('utf-8')().decode
        buffer = ""
        
        while True:
            # Read a small chunk of bytes (e.g., 10 bytes to ensure we get full characters often)
            chunk_bytes = await process.stdout.read(10)
            if not chunk_bytes:
                break
            
            buffer += decoder(chunk_bytes)

            # Try to find a word boundary (space or common punctuation)
            match = re.search(r'([\s.,;!?:])', buffer) # Match space or common punctuation
            
            if match:
                # Yield everything before the delimiter as a 'word'
                yield buffer[:match.start()], ""
                # Yield the delimiter itself
                yield match.group(0), ""
                # Remove yielded content from buffer
                buffer = buffer[match.end():]
            elif len(buffer) >= 5: # If no delimiter, but buffer is growing, yield a chunk for non-space-delimited languages
                yield buffer[:5], ""
                buffer = buffer[5:]

        # After the loop, flush any remaining characters from the decoder
        buffer += decoder(b'', final=True)
        if buffer:
            yield buffer, ""

    else:
        stdout, stderr = await process.communicate()
        yield stdout.decode(), stderr.decode()