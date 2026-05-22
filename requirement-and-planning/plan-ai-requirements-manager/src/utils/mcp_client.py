"""
MCP Client utilities

This module provides a generic MCP client that communicates with MCP servers
via stdio (standard input/output). It has no knowledge of JIRA or any specific
MCP server implementation.
"""

from typing import Dict, Any
import logging
import os
import sys
import subprocess
import json
import threading
import queue
from dotenv import load_dotenv

load_dotenv()

# Configure logging based on environment
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
logger = logging.getLogger(__name__)

# MCP server configuration - MUST be set in environment variables
MCP_SERVER_SCRIPT = os.getenv("MCP_SERVER_SCRIPT")
if not MCP_SERVER_SCRIPT:
    raise ValueError(
        "MCP_SERVER_SCRIPT environment variable is required. "
        "Please set it in your .env file to point to your MCP server script."
    )

# Global MCP server process
_mcp_process = None
_mcp_lock = threading.Lock()
_request_id = 0
_mcp_initialized = False


def _initialize_mcp_server(process):
    """Initialize the MCP server with the required handshake."""
    global _mcp_initialized

    if _mcp_initialized:
        return True

    try:
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "ai-requirements-manager",
                    "version": "1.0.0"
                }
            }
        }

        logger.debug(f"Sending initialize request: {json.dumps(init_request)}")

        try:
            process.stdin.write(json.dumps(init_request) + "\n")
            process.stdin.flush()
        except (OSError, BrokenPipeError) as e:
            logger.error(f"Failed to write initialize request to MCP server: {e}")
            return False

        # Read initialize response with timeout
        import select
        import time

        start_time = time.time()
        timeout = 5  # 5 seconds timeout

        while time.time() - start_time < timeout:
            # Check if process is still running
            if process.poll() is not None:
                stderr_output = process.stderr.read()
                logger.error(f"MCP server process died. stderr: {stderr_output}")
                return False

            # Check if there's data to read
            if process.stdout in select.select([process.stdout], [], [], 0.1)[0]:
                response_line = process.stdout.readline()
                logger.debug(f"Initialize response: {response_line}")

                if response_line:
                    response = json.loads(response_line)
                    if "result" in response:
                        logger.info("MCP server initialized successfully")
                        _mcp_initialized = True

                        # Send initialized notification
                        initialized_notification = {
                            "jsonrpc": "2.0",
                            "method": "notifications/initialized"
                        }
                        try:
                            process.stdin.write(json.dumps(initialized_notification) + "\n")
                            process.stdin.flush()
                        except (OSError, BrokenPipeError) as e:
                            logger.warning(f"Failed to send initialized notification: {e}")
                            # Non-fatal — server is already initialized

                        return True
                    elif "error" in response:
                        logger.error(f"MCP server initialization error: {response['error']}")
                        return False

        logger.error("MCP server initialization timed out")
        return False

    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def _validate_mcp_server_path(script_path: str) -> str:
    """
    Validate MCP server script path for security.

    Prevents path traversal, symlink attacks, and arbitrary script execution.
    Symlinks are rejected because they can redirect execution to an attacker-controlled
    script outside the intended directory, bypassing path-based access controls.

    Security: Set MCP_SERVER_SCRIPT to the absolute path of a trusted Python file.
    Do not point it at user-writable or world-writable locations.

    MCP Server Security: Customer responsibility includes securing the MCP server
    script path, preventing unauthorized modifications, and validating server
    authenticity. AWS secures the underlying compute infrastructure.

    Args:
        script_path: Path to MCP server script

    Returns:
        Resolved absolute path if valid

    Raises:
        ValueError: If path is invalid or insecure
    """
    if not script_path:
        raise ValueError("MCP server script path cannot be empty")

    # Resolve to absolute path (resolves symlinks and ..)
    abs_path = os.path.realpath(script_path)

    # Check if file exists
    if not os.path.isfile(abs_path):
        raise ValueError(f"MCP server script not found: {abs_path}")

    # Check if it's a Python file
    if not abs_path.endswith('.py'):
        raise ValueError(f"MCP server script must be a Python file: {abs_path}")

    # Reject symlinks to prevent symlink-based path traversal
    if os.path.islink(script_path):
        raise ValueError(f"MCP server script must not be a symlink: {script_path}")

    # Check file is not world-writable (basic integrity check)
    file_stat = os.stat(abs_path)
    if file_stat.st_mode & 0o002:
        raise ValueError(f"MCP server script must not be world-writable: {abs_path}")

    return abs_path


def _start_mcp_server():
    """Start the MCP server process if not already running."""
    global _mcp_process, _mcp_initialized

    with _mcp_lock:
        if _mcp_process is None or _mcp_process.poll() is not None:
            try:
                # Validate and resolve MCP server path
                validated_script_path = _validate_mcp_server_path(MCP_SERVER_SCRIPT)
            except ValueError as e:
                raise ValueError(f"Invalid MCP server script path: {e}") from e

            logger.info(f"Starting MCP server: {validated_script_path}")

            # Determine the Python interpreter to use.
            # Prefer MCP_PYTHON env var for explicit override, then fall back to
            # the project venv, then the script directory venv, then system Python.
            mcp_dir = os.path.dirname(validated_script_path)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

            # Allow explicit override via environment variable
            mcp_python_override = os.getenv("MCP_PYTHON")

            # Build candidate list
            venv_paths = []
            if mcp_python_override:
                venv_paths.append(mcp_python_override)

            venv_paths += [
                os.path.join(project_root, ".venv", "bin", "python3"),
                os.path.join(project_root, "venv", "bin", "python3"),
                os.path.join(mcp_dir, ".venv", "bin", "python3"),
                os.path.join(mcp_dir, "venv", "bin", "python3"),
                os.path.join(project_root, ".venv", "bin", "python"),
                os.path.join(project_root, "venv", "bin", "python"),
                os.path.join(mcp_dir, ".venv", "bin", "python"),
                os.path.join(mcp_dir, "venv", "bin", "python"),
            ]

            python_cmd = None
            for venv_python in venv_paths:
                try:
                    # Use the path as-is (do not resolve symlinks) so we stay
                    # inside the venv's site-packages rather than the base interpreter.
                    if os.path.isfile(venv_python) and os.access(venv_python, os.X_OK):
                        # Verify mcp is importable with this interpreter
                        check = subprocess.run(
                            [venv_python, "-c", "import mcp"],
                            capture_output=True, timeout=5
                        )
                        if check.returncode == 0:
                            python_cmd = venv_python
                            logger.info(f"Using Python interpreter with mcp: {python_cmd}")
                            break
                        else:
                            logger.debug(f"mcp not available in {venv_python}, skipping")
                except (OSError, subprocess.TimeoutExpired) as e:
                    logger.debug(f"Could not check {venv_python}: {e}")
                    continue

            if not python_cmd:
                # Last resort: use the same Python running this process
                python_cmd = sys.executable
                logger.warning(f"No venv with mcp found, using current interpreter: {python_cmd}")

            try:
                # Use validated, resolved paths — shell=False prevents shell injection.
                # Communication uses stdio (JSON-RPC over stdin/stdout) on the same host.
                # This is local IPC, not network traffic — protected by OS process isolation.
                # JIRA credentials are managed by the MCP server externally.
                _mcp_process = subprocess.Popen(
                    [python_cmd, validated_script_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )
            except (OSError, subprocess.SubprocessError) as e:
                raise RuntimeError(f"Failed to start MCP server process: {e}") from e

            _mcp_initialized = False
            logger.info("MCP server started")

            # Initialize the server
            if not _initialize_mcp_server(_mcp_process):
                raise RuntimeError("Failed to initialize MCP server")

    return _mcp_process


def _call_mcp_tool(tool_name: str, arguments: Dict[str, Any], timeout: int = None) -> Dict[str, Any]:
    """
    Call an MCP tool via the stdio protocol.

    Args:
        tool_name: Name of the MCP tool to call
        arguments: Arguments to pass to the tool
        timeout: Timeout in seconds (default from env or 30)

    Returns:
        Dict containing the tool's response
    """
    global _request_id

    # Get timeout from environment or use default
    if timeout is None:
        timeout = int(os.getenv("MCP_TIMEOUT", "30"))

    try:
        # Start MCP server if needed
        process = _start_mcp_server()

        # Generate unique request ID
        _request_id += 1
        request_id = _request_id

        # Prepare MCP request
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        logger.debug(f"Sending MCP request: {json.dumps(request)}")

        # Send request
        request_json = json.dumps(request) + "\n"
        try:
            process.stdin.write(request_json)
            process.stdin.flush()
        except (OSError, BrokenPipeError) as e:
            raise RuntimeError(f"Failed to write to MCP server stdin: {e}") from e

        # Read response with timeout
        response_queue = queue.Queue()

        def read_response():
            try:
                line = process.stdout.readline()
                if line:
                    response_queue.put(("success", line))
                else:
                    response_queue.put(("error", "No response from MCP server"))
            except OSError as e:
                response_queue.put(("error", f"Failed to read MCP server stdout: {e}"))
            except Exception as e:
                response_queue.put(("error", str(e)))

        reader_thread = threading.Thread(target=read_response)
        reader_thread.daemon = True
        reader_thread.start()

        try:
            status, result = response_queue.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(f"MCP tool {tool_name} timed out after {timeout} seconds")

        if status == "error":
            raise Exception(f"MCP communication error: {result}")

        logger.debug(f"Received MCP response: {result}")

        # Parse response
        response = json.loads(result)

        if "error" in response:
            error = response["error"]
            raise Exception(f"MCP tool error: {error.get('message', 'Unknown error')}")

        if "result" in response:
            result_data = response["result"]

            # Handle different response formats
            if isinstance(result_data, dict):
                # Check for content array (MCP protocol format)
                if "content" in result_data:
                    content = result_data["content"]
                    if isinstance(content, list) and len(content) > 0:
                        text = content[0].get("text", "{}")
                        # Try to parse as JSON
                        try:
                            return json.loads(text) if isinstance(text, str) else text
                        except json.JSONDecodeError:
                            return {"text": text}

                # Direct result
                return result_data

            return {"result": result_data}

        raise Exception("Invalid MCP response format")

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse MCP response: {str(e)}")
        raise Exception(f"Failed to parse MCP response: {str(e)}")
    except Exception as e:
        logger.warning(f"MCP tool call failed: {str(e)}")
        raise


def _stop_mcp_server():
    """Stop the MCP server process."""
    global _mcp_process, _mcp_initialized

    with _mcp_lock:
        if _mcp_process is not None:
            logger.info("Stopping MCP server")
            try:
                _mcp_process.terminate()
                try:
                    _mcp_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning("MCP server did not terminate gracefully; killing process")
                    _mcp_process.kill()
                    try:
                        _mcp_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        logger.error("MCP server process could not be killed")
            except OSError as e:
                logger.error(f"Error stopping MCP server: {e}")
            finally:
                _mcp_process = None
                _mcp_initialized = False
            logger.info("MCP server stopped")


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any], timeout: int = None) -> Dict[str, Any]:
    """
    Call any MCP tool with the given arguments.

    This is a generic function that works with any MCP server and tool.
    It has no knowledge of what the tool does or what service it integrates with.

    Args:
        tool_name: Name of the MCP tool to call (e.g., "jira_create_issue")
        arguments: Arguments to pass to the tool
        timeout: Timeout in seconds (default from env or 30)

    Returns:
        Dict containing the tool's response

    Raises:
        Exception: If the MCP call fails
    """
    # Get timeout from environment if not specified
    if timeout is None:
        timeout = int(os.getenv("MCP_TIMEOUT", "30"))

    return _call_mcp_tool(tool_name, arguments, timeout)


def create_jira_issue(
    project_key: str,
    summary: str,
    description: str,
    issue_type: str,
    parent_epic: str = None,
    story_points: int = None
) -> Dict[str, Any]:
    """
    Create a JIRA issue using the MCP server.

    This is a convenience wrapper around call_mcp_tool for creating JIRA issues.
    Returns a dict with 'key', 'id', and other fields from the response.
    """
    arguments = {
        "project_key": project_key,
        "summary": summary,
        "description": description,
        "issue_type": issue_type
    }

    if parent_epic:
        arguments["parent_epic"] = parent_epic

    if story_points is not None:
        arguments["story_points"] = story_points

    result = call_mcp_tool("jira_create_issue", arguments)

    # Parse the response to extract key
    if isinstance(result, dict):
        # If already parsed as JSON with key field
        if 'key' in result:
            return result

        # If it's a text response, try to extract key
        if 'text' in result:
            import re
            text = result['text']

            # Try to extract key from text
            key_match = re.search(r'Key:\s*([A-Z]+-\d+)', text)
            if key_match:
                result['key'] = key_match.group(1)

            # Try to extract full JSON response
            json_match = re.search(r'Full Response:\s*(\{.*?\})', text, re.DOTALL)
            if json_match:
                try:
                    import json
                    issue_data = json.loads(json_match.group(1))
                    result.update(issue_data)
                except json.JSONDecodeError:
                    pass

    return result


# Cleanup function to stop MCP server on exit
import atexit
atexit.register(_stop_mcp_server)
