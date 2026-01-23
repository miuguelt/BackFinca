
import threading
import sys
import traceback
import logging
import gc
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def dump_threads():
    """Dump stack traces of all running threads."""
    id2name = {t.ident: t.name for t in threading.enumerate()}
    code = []
    for threadId, stack in sys._current_frames().items():
        name = id2name.get(threadId, "")
        code.append(f"\nThread: {name}({threadId})")
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append(f'  File: "{filename}", line {lineno}, in {name}')
            if line:
                code.append(f'    {line}')
    return "\n".join(code)

def inspect_executors():
    """Find and inspect ThreadPoolExecutor instances in memory."""
    executors = []
    try:
        # Search for TPE instances
        for obj in gc.get_objects():
            if isinstance(obj, ThreadPoolExecutor):
                executors.append({
                    'id': id(obj),
                    'shutdown': getattr(obj, '_shutdown', 'unknown'),
                    'broken': getattr(obj, '_broken', 'unknown'),
                    'queue_size': getattr(obj, '_work_queue', []) and getattr(obj._work_queue, 'qsize', lambda: -1)(),
                    'threads': len(getattr(obj, '_threads', []))
                })
    except Exception as e:
        logger.error(f"Error inspecting executors: {e}")
        return {'error': str(e)}
    
    return {'count': len(executors), 'details': executors}
