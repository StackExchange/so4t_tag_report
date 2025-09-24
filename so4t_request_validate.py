# Third-party libraries
import time
import socket

retry_count = 0
max_retries = 3
timeout = 10

def handle_except(ex):
    name = ex.__class__.__name__
    global timeout
    match name:
        case "Timeout":
            message = f"Request timed out after {timeout} seconds."
        case "ReadTimeout":
            message = f"Reading response timed out after {timeout} seconds."
        case "ConnectionError":
            # Connection reset by peer (errno 104) can be transient
            conn_err = False
            try:
                conn_err = isinstance(ex.args[0], socket.error) and ex.args[0].errno == 104
            except Exception:
                conn_err = False
            
            if conn_err:
                message = f"Connection was unexpectedly reset."
            elif "Read timed out" in str(ex):
                message = f"Reading response timed out after {timeout} seconds."
            else:
                print(f"Unexpected connection error occurred: {ex}")
                raise SystemExit
        case _:
             print(f"An unhandled error occurred: {ex}")
             raise SystemExit
    global retry_count
    retry_count += 1
    if retry_count > max_retries:
        print(f"{message} Reached max retries ({max_retries}).")
        raise SystemExit
    print(f"{message} Retrying... ({retry_count}/{max_retries})")
    backoff = 2 ** retry_count
    time.sleep(backoff)
