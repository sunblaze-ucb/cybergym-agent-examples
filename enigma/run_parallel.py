import concurrent.futures
import logging
import os
import time
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path

import httpx
from run import EnigmaArgs, TaskArgs, run_with_configs
from simple_parsing import ArgumentParser
from tqdm import tqdm

from cybergym.task.types import TaskDifficulty

API_KEY = os.getenv("CYBERGYM_API_KEY")
API_KEY_NAME = "X-API-Key"
START_RANDOM_DELAY = 10


# Configure logger
logger = logging.getLogger(__name__)


@dataclass
class ParallelArgs:
    log_dir: Path
    """Directory to save the logs"""

    tmp_dir: Path
    """Directory to save the temporary files"""

    data_dir: Path
    """Directory containing the data files"""

    server: str
    """Server address for the tasks"""

    task_ids: list[str] = field(default_factory=list)
    """List of task IDs to run"""

    task_ids_file: Path | None = None
    """File containing task IDs, one per line"""

    models: list[str] = field(default_factory=list)
    """List of models to use for generation"""

    difficulties: list[TaskDifficulty] = field(default_factory=list)
    """List of difficulty levels to run"""

    max_workers: int = 4
    """Maximum number of parallel workers"""

    # Default EnigmaArgs values
    cost_limit: float = 2.0
    """Cost limit for the Enigma task in Dollars"""

    repo: Path = None
    """Path to the repo (defaults to the repo path from run.py)"""

    enigma_python: Path = None
    """Path to the enigma python executable"""

    timeout: int = 3600
    """Timeout for the task in seconds"""

    max_retries: int = 3
    """Maximum number of retries for each task"""


def run_verify(agent_id: str, server: str):
    with httpx.Client(base_url=server, timeout=1200) as client:
        headers = {
            API_KEY_NAME: API_KEY,
        }
        try:
            response = client.post(
                "/verify-agent-pocs",
                json={"agent_id": agent_id},
                headers=headers,
            )
            logger.info(f"Verification response for agent {agent_id}: {response.status_code} {response.text}")
        except httpx.ReadTimeout:
            logger.warning(f"Verification request timed out for agent {agent_id}")
        except Exception as e:
            logger.error(f"Error during verification for agent {agent_id}: {e}")


def run_task(task_config: tuple, parallel_args: ParallelArgs, task_index: int) -> None:
    """Run a single task with the specified configuration."""
    # Configure separate worker logger if not already configured
    import os
    os.makedirs("workers", exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    for h in logger.handlers:
        logger.removeHandler(h)
    h = logging.FileHandler(f"workers/worker_{os.getpid()}.log")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    h.setFormatter(formatter)
    logger.addHandler(h)

    time.sleep(task_index % START_RANDOM_DELAY)
    task_id, model, difficulty = task_config

    try:
        for attempt in range(parallel_args.max_retries):
            logger.info(f"Starting task {task_index}: {task_id} with model {model}, difficulty {difficulty}")

            # Create EnigmaArgs
            enigma_args = EnigmaArgs(
                model=model,
                log_dir=parallel_args.log_dir,
                tmp_dir=parallel_args.tmp_dir,
                repo=parallel_args.repo,
                enigma_python=parallel_args.enigma_python,
                cost_limit=parallel_args.cost_limit,
                silent=True,
                timeout=parallel_args.timeout,
            )

            # Create TaskArgs
            task_args = TaskArgs(
                task_id=task_id,
                data_dir=parallel_args.data_dir,
                server=parallel_args.server,
                difficulty=difficulty,
            )

            # Run the task
            agent_id = run_with_configs(enigma_args, task_args)
            if agent_id is not None:
                logger.info(f"Completed task {task_index}: {task_id} with model {model}, difficulty {difficulty}")
                run_verify(agent_id, parallel_args.server)
                break
            logger.warning(f"Task {task_index} {task_config} failed validation, retrying... (attempt {attempt + 1})")
    except Exception as e:
        logger.error(f"Error running task {task_index} ({task_id}, {model}, {difficulty}): {e}")


def load_task_ids_from_file(filepath: Path) -> list[str]:
    """Load task IDs from a file, one task ID per line."""
    if not filepath.exists():
        raise FileNotFoundError(f"Task IDs file not found: {filepath}")

    with open(filepath) as f:
        # Strip whitespace and filter out empty lines
        task_ids = [line.strip() for line in f.readlines()]
        task_ids = [task_id for task_id in task_ids if task_id]

    return task_ids


def main():
    global START_RANDOM_DELAY
    parser = ArgumentParser(description="Run Enigma tasks in parallel")
    parser.add_arguments(ParallelArgs, dest="parallel_args")
    parser.add_argument(
        "--log_level", type=str, default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    args = parser.parse_args()
    parallel_args = args.parallel_args
    START_RANDOM_DELAY = parallel_args.max_workers

    logger.setLevel(args.log_level)

    # Set default repo path if not provided
    if parallel_args.repo is None:
        from run import SCRIPT_DIR

        parallel_args.repo = SCRIPT_DIR / "enigma-repo"

    if parallel_args.task_ids_file:
        try:
            file_task_ids = load_task_ids_from_file(parallel_args.task_ids_file)
            logger.info(f"Loaded {len(file_task_ids)} task IDs from {parallel_args.task_ids_file}")
            # Combine command line task IDs with those from the file
            parallel_args.task_ids = parallel_args.task_ids + file_task_ids
        except Exception as e:
            logger.error(f"Error loading task IDs from file: {e}")
            return

    # Create all combinations of task configurations
    task_configs = list(product(parallel_args.task_ids, parallel_args.models, parallel_args.difficulties))
    total_tasks = len(task_configs)

    if total_tasks == 0:
        logger.error("No tasks to run. Please specify task_ids, models, and difficulties.")
        return

    logger.info(f"Running {total_tasks} tasks across {parallel_args.max_workers} workers")

    # Ensure directories exist
    parallel_args.log_dir.mkdir(parents=True, exist_ok=True)
    parallel_args.tmp_dir.mkdir(parents=True, exist_ok=True)

    # Run tasks in parallel with progress bar
    with concurrent.futures.ProcessPoolExecutor(max_workers=parallel_args.max_workers) as executor:
        futures = {
            executor.submit(run_task, task_config, parallel_args, i): i for i, task_config in enumerate(task_configs)
        }

        # Create progress bar
        with tqdm(total=total_tasks, desc="Executing tasks", unit="task") as progress_bar:
            # Wait for all tasks to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    task_idx = futures[future]
                    task_config = task_configs[task_idx]
                    logger.error(f"Task execution failed for {task_config}: {e}")
                finally:
                    # Update progress bar for each completed task
                    progress_bar.update(1)

    logger.info(f"Completed all {total_tasks} tasks")


if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    run_logger = logging.getLogger("run")
    run_logger.setLevel(logging.WARNING)

    main()