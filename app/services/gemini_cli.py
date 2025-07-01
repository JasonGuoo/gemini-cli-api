import asyncio
import os
from typing import AsyncGenerator, Tuple
from app.config import GEMINI_CLI_PATH

async def execute_gemini_command(prompt: str, stream: bool = False) -> AsyncGenerator[Tuple[str, str], None]:
    """
    Executes the gemini CLI with a given prompt and streams the output.
    """
    cmd = [GEMINI_CLI_PATH, "--prompt", prompt]

    # Pass the current environment variables to the subprocess
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ
    )

    if stream:
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            yield line.decode(), ""
    else:
        stdout, stderr = await process.communicate()
        yield stdout.decode(), stderr.decode()