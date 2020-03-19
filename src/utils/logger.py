import time
from datetime import datetime

class Logger:
    """A simple class for writing log messages. 

    Attributes:
        printing (optional): A boolean variable indicating whether logs should be printed to console/terminal output.
        log_file (optional): A name for a log file (in the root of the application) where log messages should be written.
    """

    def __init__(self, printing: bool = False, log_file: str = None):
        self.printing = printing
        self.log_file = log_file

    def print_log(self, text, level):
        """Prints a log message to console/terminal and/or to a log file (if specified at init). The log message is prefixed
        with current time and the given logging level.
        """
        log_prefix = datetime.utcnow().strftime('%y/%m/%d %H:%M:%S') + ' ['+ level +'] '
        log_text = log_prefix + text
        if (self.printing == True):
            print(log_text)
        if (self.log_file is not None):
            with open(self.log_file, 'a') as the_file:
                the_file.write(log_text + '\n')

    def debug(self, text: str):
        self.print_log(text, 'DEBUG')

    def info(self, text: str):
        self.print_log(text, 'INFO')

    def warning(self, text: str):
        self.print_log(text, 'WARNING')

    def error(self, text: str):
        self.print_log(text, 'ERROR')

    def duration(self, time1, text, round_n: int = 3, unit: str = 'ms') -> None:
        """Creates a log message that contains the duration between the current time and a given time [time1].
        """
        log_str = ''
        if (unit == 's'):
            time_elapsed = round(time.time() - time1, round_n)
            log_str = '--- %s s --- %s' % (time_elapsed, text)
        elif (unit == 'ms'):
            time_elapsed = round((time.time() - time1) * 1000)
            log_str = '--- %s ms --- %s' % (time_elapsed, text)

        self.print_log(log_str, 'INFO')