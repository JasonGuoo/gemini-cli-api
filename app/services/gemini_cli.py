import asyncio
import os
import uuid
from typing import AsyncGenerator, Tuple

class GeminiCLIProcess:
    """
    Encapsulates a single gemini CLI subprocess.
    Manages its lifecycle (start, stop) and interaction (sending commands, receiving output).
    """
    def __init__(self, cli_path: str):
        self.cli_path = cli_path
        self.process = None
        # Define a unique delimiter to signal the end of output from the gemini CLI.
        # IMPORTANT: The gemini CLI MUST be configured or modified to print this
        # delimiter after every command's output for execute_command to work reliably.
        # If the gemini CLI does not support printing a custom delimiter, this design
        # will need to be revisited.
        self.delimiter = f"---END_OF_GEMINI_OUTPUT_{uuid.uuid4()}---"

    async def start(self):
        """
        Starts the gemini CLI subprocess.
        Configures stdin, stdout, and stderr to be pipes for programmatic interaction.
        Passes the current environment variables to the subprocess.
        """
        if self.process and self.process.returncode is None:
            # Process is already running
            return

        # Pass the current environment variables to the subprocess.
        # This is crucial for passing API keys and other configurations from .env
        # that are loaded into os.environ by python-dotenv.
        current_env = os.environ.copy()

        self.process = await asyncio.create_subprocess_exec(
            self.cli_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=current_env,
        )
        print(f"[GEMINI CLI] Process started: PID {self.process.pid}")

    async def execute_command(self, command: str, timeout: int, stream: bool = False) -> AsyncGenerator[Tuple[str, str], None]:
        """
        Sends a command to the running gemini CLI subprocess and reads its response.
        If stream is True, yields chunks of stdout and stderr as they become available.
        Otherwise, returns the full stdout and stderr after the delimiter is found.
        Assumes the gemini CLI will print a unique delimiter after its output.
        """
        if not self.process or self.process.returncode is not None:
            raise RuntimeError("Gemini CLI process is not running or has terminated.")

        print(f"[GEMINI CLI] Sending command: {command}")
        # Append the delimiter to the command.
        # This assumes the gemini CLI will execute this as part of its input
        # and print the delimiter to stdout after its response.
        command_to_send = f"{command}\n{self.delimiter}\n"

        stdout_buffer = []
        stderr_buffer = []

        try:
            # Write the command to stdin
            self.process.stdin.write(command_to_send.encode('utf-8'))
            await self.process.stdin.drain() # Ensure the data is sent

            # Read from stdout until the delimiter is found or timeout
            while True:
                try:
                    # Read a line from stdout
                    line = await asyncio.wait_for(self.process.stdout.readline(), timeout=timeout)
                    if not line: # EOF reached, process might have exited unexpectedly
                        print("[GEMINI CLI] STDOUT: EOF reached unexpectedly.")
                        break
                    decoded_line = line.decode('utf-8').strip()

                    # Print to console for debugging
                    if decoded_line and self.delimiter not in decoded_line:
                        print(f"[GEMINI CLI] STDOUT: {decoded_line}")

                    # Check for the delimiter
                    if self.delimiter in decoded_line:
                        # Remove the delimiter from the line and yield/buffer the rest
                        content_before_delimiter = decoded_line.replace(self.delimiter, '').strip()
                        if content_before_delimiter:
                            if stream:
                                yield content_before_delimiter, ""
                            else:
                                stdout_buffer.append(content_before_delimiter)
                        break # End of output
                    
                    # If not delimiter, yield/buffer the line
                    if stream:
                        yield decoded_line, ""
                    else:
                        stdout_buffer.append(decoded_line)

                except asyncio.TimeoutError:
                    # If stdout times out, try to read stderr before raising
                    try:
                        stderr_output = await asyncio.wait_for(self.process.stderr.read(), timeout=1)
                        if stderr_output:
                            decoded_stderr = stderr_output.decode('utf-8').strip()
                            print(f"[GEMINI CLI] STDERR (on timeout): {decoded_stderr}")
                            stderr_buffer.append(decoded_stderr)
                    except asyncio.TimeoutError:
                        pass # Ignore if stderr read also times out
                    raise TimeoutError(f"Gemini CLI command timed out after {timeout} seconds.")
                except Exception as e:
                    # Catch other potential errors during readline
                    print(f"[GEMINI CLI] Error reading from stdout: {e}")
                    raise RuntimeError(f"Error reading from Gemini CLI stdout: {e}")

                # Read any available stderr output non-blockingly during streaming
                try:
                    while True:
                        stderr_chunk = self.process.stderr.read(1024) # Read a small chunk
                        if not stderr_chunk:
                            break
                        decoded_stderr_chunk = stderr_chunk.decode('utf-8')
                        if decoded_stderr_chunk:
                            print(f"[GEMINI CLI] STDERR: {decoded_stderr_chunk.strip()}")
                            if stream:
                                yield "", decoded_stderr_chunk # Yield stderr as well
                            else:
                                stderr_buffer.append(decoded_stderr_chunk)
                except BlockingIOError:
                    pass # No more data currently available on stderr

        except Exception as e:
            # If any error occurs, try to read remaining output before re-raising
            print(f"[GEMINI CLI] Exception during command execution: {e}")
            try:
                # Use communicate() to drain pipes and wait for process to finish if it's still running
                stdout_comm, stderr_comm = await asyncio.wait_for(self.process.communicate(), timeout=1)
                if stdout_comm:
                    decoded_stdout_comm = stdout_comm.decode('utf-8').strip()
                    print(f"[GEMINI CLI] STDOUT (on exception): {decoded_stdout_comm}")
                    if stream:
                        yield decoded_stdout_comm, ""
                    else:
                        stdout_buffer.append(decoded_stdout_comm)
                if stderr_comm:
                    decoded_stderr_comm = stderr_comm.decode('utf-8').strip()
                    print(f"[GEMINI CLI] STDERR (on exception): {decoded_stderr_comm}")
                    if stream:
                        yield "", decoded_stderr_comm
                    else:
                        stderr_buffer.append(decoded_stderr_comm)
            except asyncio.TimeoutError:
                print("[GEMINI CLI] communicate() also timed out on exception.")
                pass # Ignore if communicate also times out
            except Exception as comm_e:
                print(f"[GEMINI CLI] Error during communicate fallback: {comm_e}") # Log internal error

            # Re-raise the original exception
            raise e

        if not stream:
            final_stdout = "\n".join(stdout_buffer).strip()
            final_stderr = "\n".join(stderr_buffer).strip()
            yield final_stdout, final_stderr

    async def stop(self):
        """
        Terminates the gemini CLI subprocess.
        """
        if self.process:
            print(f"[GEMINI CLI] Terminating process: PID {self.process.pid}")
            self.process.terminate() # Send SIGTERM
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5) # Wait for it to exit
                print(f"[GEMINI CLI] Process PID {self.process.pid} terminated gracefully.")
            except asyncio.TimeoutError:
                self.process.kill() # Force kill if it doesn't terminate gracefully
                await self.process.wait()
                print(f"[GEMINI CLI] Process PID {self.process.pid} force-killed.")
            self.process = None
