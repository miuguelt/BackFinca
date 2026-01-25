import sys
import os

print(f"Python Executable: {sys.executable}")
print(f"Version: {sys.version}")
print("sys.path:")
for p in sys.path:
    print(f"  {p}")

try:
    import flask_caching
    print(f"SUCCESS: flask_caching imported from {flask_caching.__file__}")
except ImportError as e:
    print(f"FAILURE: Could not import flask_caching: {e}")

try:
    import jsonschema
    print(f"jsonschema version: {jsonschema.__version__}")
except ImportError:
    print("Could not import jsonschema")
