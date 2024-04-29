import json
import os
from pathlib import Path
from datetime import datetime

class Utils(object):
    FOLDER_LOGS = "logs"
    EXT_LOGS = ".applog"

    # Methods
    @staticmethod
    # Clear old log files
    def clear_logs():
        Utils.log("Start deleting older log files..")
        log_path_files = os.listdir(Utils.FOLDER_LOGS)
        for item in log_path_files:
            if item.endswith(Utils.EXT_LOGS):
                logfile: str = os.path.join(Utils.FOLDER_LOGS, item)
                if os.path.isfile(logfile):
                    os.remove(logfile)

        Utils.log("Done deleting old log files.")

    @staticmethod
    def write_to_log(content: str, fileprefix: str) -> bool:
        try:
            Path(Utils.FOLDER_LOGS).mkdir(parents=True, exist_ok=True)
            filename: str = f"{fileprefix}_{datetime.today().strftime('%Y-%m-%d')}{Utils.EXT_LOGS}"
            filepath: str = os.path.join(Utils.FOLDER_LOGS, filename)
            with open(filepath, 'a') as f:
                f.write(f"{content}\n")
            return True
        except Exception as e:
            #Utils.log_err("Error", e)
            return False

    @staticmethod
    def log(content: str):
        print(f"{content}")
        Utils.write_to_log(content, "log")

    @staticmethod
    def log_err(content: str, err: Exception):
        to_write: str = f"{content} => {err}"
        print(to_write)
        Utils.write_to_log(to_write, "errlog")

    @staticmethod
    def pop_first_line(file: str) -> str:
        with open(file, 'r+') as f: # open file in read / write mode
            firstLine = f.readline() # read the first line and throw it out
            data = f.read() # read the rest
            f.seek(0) # set the cursor to the top of the file
            f.write(data) # write the data back
            f.truncate() # set the file size to the current size
            return firstLine
        return ""

    @staticmethod
    def append_file(filename: str, content: str) -> bool:
        try:
            with open(filename, 'a', encoding = 'utf8') as f:
                f.write(content)
            return True
        except Exception as e:
            Utils.log_err("Error", e)
            return False

    @staticmethod
    def write_file(filename: str, content: str) -> bool:
        try:
            with open(filename, 'w', encoding = 'utf8') as f:
                f.write(content)
            return True
        except Exception as e:
            Utils.log_err("Error", e)
            return False

    @staticmethod
    def write_json(filename: str, content: any) -> bool:
        try:
            with open(filename, 'w') as f:
                json.dump(content, f, indent = 4)
            return True
        except Exception as e:
            Utils.log_err("Error", e)
            return False

    @staticmethod
    def read_file(filename: str) -> str:
        try:
            contents = ""
            with open(filename) as file:
                contents = file.read()

            return contents
        except Exception as e:
            Utils.log_err("Error", e)
            return ""

    @staticmethod
    def read_json(filename: str) -> any:
        try:
            contents = None
            with open(filename) as file:
                contents = json.loads(file.read())

            return contents
        except Exception as e:
            Utils.log_err("Error", e)
            return None
