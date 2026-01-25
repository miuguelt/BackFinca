import subprocess
import time
import sys
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [RESTART_MANAGER] - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('server_monitor.log')
    ]
)

def run_server():
    """
    Runs the server using python run.py in a loop.
    If the server crashes (exit code != 0), it restarts it.
    If the server exits normally (exit code 0), it stops (assumed manual stop).
    """
    cmd = [sys.executable, "run.py"]
    
    # Pass through environment variables
    env = os.environ.copy()
    
    restart_count = 0
    
    logging.info("Starting server monitor...")

    while True:
        try:
            logging.info(f"Launching server (Attempt #{restart_count + 1})...")
            
            # Start the process
            process = subprocess.Popen(cmd, env=env)
            process_pid = process.pid
            logging.info(f"Server started with PID: {process_pid}")
            
            # Wait for the process to complete
            exit_code = process.wait()
            
            logging.info(f"Server exited with code: {exit_code}")
            
            if exit_code == 0:
                logging.info("Server exited normally. Stopping monitor.")
                break
            else:
                logging.error("Server crashed! Restarting in 5 seconds...")
                restart_count += 1
                time.sleep(5)
                
        except KeyboardInterrupt:
            logging.info("Monitor stopping by user request (Ctrl+C).")
            # Try to kill the subprocess if it's running
            try:
                if 'process' in locals() and process.poll() is None:
                    logging.info("Terminating server process...")
                    process.terminate()
                    process.wait(timeout=5)
            except Exception as e:
                logging.error(f"Error checking/terminating process: {e}")
            break
        except Exception as e:
            logging.critical(f"Critical error in monitor: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_server()
