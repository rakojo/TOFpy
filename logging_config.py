import logging

LOG_FILE_NAME = "log.txt"
LOG_FILE_MAX_SIZE = 1024 * 1024 * 10  # 10 MB 


_initialized = False    # Module-level variable to track initialization

def backup_log_file_if_big():
    """
    Rename the log file if its size is bigger than the given size.
    """
    global _initialized
    if not _initialized:
        import os
        # if file exists 
        if os.path.exists(LOG_FILE_NAME):
            # check the size of the file        
            if os.path.getsize(LOG_FILE_NAME) > LOG_FILE_MAX_SIZE:
                # date time string to append to the file name
                # remanme the file
                import datetime
                data_time_str = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                os.rename(LOG_FILE_NAME, f"log_old_{data_time_str}.txt")
                _initialized = True  # Set the flag to True to indicate that initialization has been done

backup_log_file_if_big()


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# console_handler = logging.StreamHandler()
file_handler = logging.FileHandler(LOG_FILE_NAME, mode="a", encoding="utf-8")

formatter = logging.Formatter("{asctime} - {levelname} - {message}",
                              style="{",
                              datefmt="%Y-%m-%d %H:%M:%S"
            )

file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def get_logs_after(message):
    """
    Return all log messages after the message containing the given string.
    """
    with open("log.txt", "r", encoding="utf-8") as file:
        lines = file.readlines()
        for i, line in reversed(list(enumerate(lines))):
            if message in line:
                return lines[i:]



def save_logs_after(message, to_file_name):
    """
    Save all log messages after the message containing the given string to a file.
    """
    logs = get_logs_after(message)
    with open(to_file_name, "a", encoding="utf-8") as file:
        for log in logs:
            file.write(log)


def get_last_log():
    with open("log.txt", "r", encoding="utf-8") as file:
        lines = file.readlines()
        return lines[-1]


