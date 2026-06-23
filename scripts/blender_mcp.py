"""Blender MCP client — execute Python code in the running Blender instance.

Usage:
    from blender_mcp import blender_exec
    result = blender_exec("import bpy; result = {'count': len(bpy.data.objects)}")
"""
import json
import socket
import sys

_BLENDER_HOST = "localhost"
_BLENDER_PORT = 9876
_TIMEOUT = 10


def blender_exec(code: str, timeout: float = _TIMEOUT) -> dict:
    """Execute *code* inside Blender's Python interpreter and return the result dict.

    The code **must** assign ``result = {…}`` before it finishes.
    The function returns the ``result`` dict on success, or
    ``{"status": "error", "message": "…"}`` on failure.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((_BLENDER_HOST, _BLENDER_PORT))
    req = json.dumps({"type": "execute", "code": code, "strict_json": False})
    s.sendall(req.encode() + b"\x00")
    data = b""
    while True:
        try:
            chunk = s.recv(1 << 20)
            if not chunk:
                break
            data += chunk
        except socket.timeout:
            break
    s.close()
    raw = data.decode().rstrip("\x00")
    if not raw:
        return {"status": "error", "message": "Empty response from Blender"}
    return json.loads(raw)


def blender_print(code: str, timeout: float = _TIMEOUT) -> str:
    """Execute *code* and return captured stdout, or the error message."""
    resp = blender_exec(code, timeout=timeout)
    if resp.get("status") == "error":
        return resp.get("message", "Unknown error")
    return resp.get("stdout", "") or json.dumps(resp.get("result", {}))


# ── CLI mode ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python blender_mcp.py '<code>'")
        sys.exit(1)
    print(blender_print(sys.argv[1]))
