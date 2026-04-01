# Third-party libraries
import time
import socket

retry_count = 0
max_retries = 3
timeout = 30
last_api_backoff = 0  # tracks the most recent API-level backoff duration

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
        case "ChunkedEncodingError" | "ProtocolError" | "InvalidChunkLength":
            message = f"Connection broken during response transfer."
        case _:
             print(f"An unhandled error occurred: {ex}")
             raise SystemExit
    global retry_count
    global last_api_backoff
    retry_count += 1
    if retry_count > max_retries:
        print(f"{message} Reached max retries ({max_retries}).")
        raise SystemExit
    print(f"{message} Retrying... ({retry_count}/{max_retries})")
    # Use the larger of exponential backoff or the last API-requested backoff
    backoff = max(2 ** retry_count, last_api_backoff)
    print(f"Waiting {backoff} seconds before retry...")
    time.sleep(backoff)
