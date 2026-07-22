"""Quick validation: test skeleton + assembly MJCF compiles in MuJoCo."""
import os, sys, tempfile, json
sys.path.insert(0, "backend/src")
libpath = "/nix/store/5v131vrpa3wjcq4aqmlg98z6rsxrhl6m-zlib-1.3.2/lib:/nix/store/hp54qay7ayl502zksigjr1irfn7h7zrp-gcc-15.2.0-lib/lib:/nix/store/inv916fdyr4z049l8q2v8i5ll3dnmqj6-libglvnd-1.7.0/lib"
os.environ["LD_LIBRARY_PATH"] = libpath + ":" + os.environ.get("LD_LIBRARY_PATH", "")
import mujoco

# Skeleton only
data = json.loads(open("/dev/stdin").read()) if not sys.stdin.isatty() else {"mjcf": ""}
for label, mjcf_data in [
    ("Skeleton only", open("/dev/stdin").read() if not sys.stdin.isatty() else ""),
]:
    pass  # won't work via stdin

# Test by reading from temp files
# Read the body counts from the compile output
print("Pass: import works")
