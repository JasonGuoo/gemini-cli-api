import asyncio
from typing import List
from app.services.gemini_cli import GeminiCLIProcess

class ProcessPool:
    """
    Manages a fixed-size pool of GeminiCLIProcess instances.
    Ensures a fixed number of concurrent gemini processes and handles their acquisition and release.
    """
    def __init__(self, pool_size: int, cli_path: str):
        self.pool_size = pool_size
        self.cli_path = cli_path
        self.processes: List[GeminiCLIProcess] = []
        self.available_processes = asyncio.Queue(maxsize=pool_size)

    async def initialize_pool(self):
        """
        Creates and starts all the gemini processes in the pool.
        """
        print(f"Initializing process pool with {self.pool_size} gemini CLI instances...")
        for i in range(self.pool_size):
            process = GeminiCLIProcess(self.cli_path)
            try:
                await process.start()
                self.processes.append(process)
                await self.available_processes.put(process)
                print(f"Started gemini CLI instance {i+1}/{self.pool_size}")
            except Exception as e:
                print(f"Failed to start gemini CLI instance {i+1}/{self.pool_size}: {e}")
                # Depending on severity, might want to re-raise or handle differently
                # For now, we'll just log and continue with fewer processes if possible.
        if not self.processes:
            raise RuntimeError("No gemini CLI processes could be started. Check your gemini CLI installation and PATH.")
        print("Process pool initialization complete.")

    async def acquire_process(self) -> GeminiCLIProcess:
        """
        Acquires a GeminiCLIProcess instance from the pool.
        If no process is available, it waits until one is released.
        """
        print("Acquiring gemini CLI process...")
        process = await self.available_processes.get()
        print(f"Process acquired: {process}")
        return process

    async def release_process(self, process: GeminiCLIProcess):
        """
        Releases a GeminiCLIProcess instance back to the pool, making it available for other requests.
        """
        print(f"Releasing process: {process}")
        await self.available_processes.put(process)

    async def shutdown_pool(self):
        """
        Stops all the gemini processes in the pool.
        """
        print("Shutting down process pool...")
        for process in self.processes:
            await process.stop()
            print(f"Stopped gemini CLI instance: {process}")
        print("Process pool shutdown complete.")
