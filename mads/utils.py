import os
import sys
import uuid
import time
import difflib
import datetime

try:
  import colorama
except:
  pass

def simple_error(error_type, error_prefix, error_message, error_body):
    print("") # make sure to exit the loading bar

    print(error_prefix)
    print(error_body)
    print(error_type + " : " + error_message)

    sys.exit(1)

def make_uuid():
    return str(uuid.uuid4())

def try_strip(obj):
    try:
        return obj.strip()
    except:
        return obj

def try_type(obj, typ):
    try:
        return (True, typ(obj))
    except:
       return (False, None)

def count_none(lst):
    cnt = 0
    for i in lst:
        if i == None:
            cnt += 1
    return cnt

def parse_string(string):
    strings = []
    record = None
    escape = False

    for char in string:
        if record != None:
            if char == '"' and not escape:
                strings.append(record)
                record = None
            elif escape:
                record += char
                escape = False
            else:
                if char == "\\":
                    escape = True
                    record += char
                else:
                    record += char
        else:
            if char == '"':
                record = ""
    
    return strings

def did_you_mean(term, other_terms):
    if isinstance(other_terms, dict):
        close_term = difflib.get_close_matches(term, other_terms.keys())
    else:
        close_term = difflib.get_close_matches(term, other_terms)

    if len(close_term) == 0:
        return ""
    else:
        return ", did you mean '" + close_term[0] + "'?"

class dbg(object):
    # takes the logger object for colors
    def __init__(self, logger, scope_tree, scope_lines, lines, file_name):
        self.scope_tree = scope_tree
        self.scope_lines = scope_lines
        self.lines = lines
        self.file_name = file_name

        self.c = logger.c
        self.term = logger.term
    
    def __truncate_line(self, line):
        if len(line) > self.term.columns:
            line = line[:self.term.columns-3]
            return line + self.c["blue"] + "..." + self.c["reset"], len(line)
        else:
            return line, len(line)

    def error(self, error_type, error_text, line_obj):
        #prefix = "error in file '" + self.file_name + "' on line " + str(line_obj[0]+1) + " with scope:"
        prefix = self.c["red"] + self.c["bold"] + "traceback (most recent scope change last):" + self.c["reset"]
        
        prev_scope = "<main>"
        for scope_name, scope_line in zip(self.scope_tree, self.scope_lines):
            prefix += "\n  file " + self.c["blue"] + "'" + self.file_name + "' line " + str(scope_line[0]+1) \
                + self.c["reset"] + " in " + self.c["bold"] + prev_scope + self.c["reset"]
            line, _ = self.__truncate_line("\n    " + self.lines[scope_line[1]][1])
            prefix += line
            prev_scope = scope_name
        
        body = "  file " + self.c["blue"] + "'" + self.file_name + "' line " + str(line_obj[0]+1) + self.c["reset"] \
            + " in " + self.c["bold"] + prev_scope + self.c["reset"]
        line, line_length = self.__truncate_line("\n    " + self.lines[line_obj[1]][1])
        body += line
        body += "\n    " + self.c["red"] + "^"*(line_length-5) + self.c["reset"]

        simple_error(self.c["red"] + self.c["bold"] + error_type + self.c["reset"], prefix, error_text, body)

# contains the configuration application-wide
class options(object):
    def __init__(self):
        self.log_severity = 1
        self.end_format = "json"
        self.pretty = False
        self.force = False
        self.segment = False
        self.boring = False
        self.todopath = ""
        
        self.cwd = os.getcwd()

        self.replacements = {}

        self.flags = {
            "COS": "WINDOWS" if os.name == "nt" else "POSIX",
            "CTIME": time.strftime('%X %x %Z'),
            "CWD": self.cwd
        }

        self.support = {
           "full-ref": False,
           "scene-ref": True,
           "shortcut-ref": True
        }

class logger(object):
    def __init__(self, log_severity, bar_max, colors=True):
        self.bar_max = bar_max
        self.bar_cnt = 0

        self.log_severity = log_severity
        self.colors = colors

        self.c = getcolors(colors)
        self.term = os.get_terminal_size()

        self._active_bar = True
        self._length_bar = min(self.term.columns-25, 60)
        self._max_length_bar = 0
        self._time_bar = None
        self._bar_string = ""

        # hide the cursor
        print('\033[?25l', end="")
    
    def __del__(self):
        # show the cursor
        print('\033[?25h', end="")
    
    def __calc_time(self):
        if self._time_bar == None:
            self._time_bar = time.time()
        remaining = ((time.time() - self._time_bar) / self.bar_cnt) * (self.bar_max - self.bar_cnt)
        
        mins, sec = divmod(remaining, 60)
        time_str = f"{int(mins):02}:{sec:05.2f}"
        return time_str

    # severity:
    # -1: special todo formatting
    #  0: only errors
    #  1: warnings
    #  2: major milestones
    #  3: minor milestones
    #  4: debug information
    def log(self, log_type, log_text, log_severity):
        if abs(log_severity) <= self.log_severity:
            log_type_msg = log_type
            if self._active_bar:
                print(" "*self.term.columns, end="\r")
            
            time_str = datetime.datetime.now().strftime("%m/%d %H:%M:%S.%f")[:-3]
            
            log_type = ""
            if log_severity == -1:
                log_type = self.c["bold"]   + "todo     " + self.c["reset"]
                log_text = log_text.replace("<", self.c["bold"]).replace(">", self.c["reset"])
                log_text = self.c["underline"] + log_text + self.c["reset"]
            elif log_severity == 1:
                log_type = self.c["yellow"] + "warning  " + self.c["reset"]
            elif log_severity == 2:
                log_type = self.c["green"]  + "milestone" + self.c["reset"]
            elif log_severity == 3:
                log_type = self.c["blue"]   + "info     " + self.c["reset"]
            elif log_severity == 4:
                log_type = self.c["purple"] + "debug    " + self.c["reset"]

            print("[" + time_str + "] " + log_type + ": " + log_type_msg + ": " + log_text, end="\n")

            # if log messages are printed after the loader is done
            # but before end is called
            if self.bar_cnt == self.bar_max:
                print(self._bar_string, end="\r", flush=True)
    
    def next(self, msg=None):
        self._active_bar = True

        self.bar_cnt += 1
        length = int(self._length_bar*self.bar_cnt/self.bar_max)
        whitespace = self._length_bar-length

        percent_str = str(round((self.bar_cnt/self.bar_max)*100)).rjust(3, " ") + "%"

        self._bar_string = percent_str \
            + " [" + self.c["green"] + "#"*length +  self.c["red"] + "-"*whitespace + self.c["reset"] + "] " \
            + self.c["bold"] + self.__calc_time() + " " \
            + str(self.bar_cnt) + "/" + str(self.bar_max) + self.c["reset"]

        print(self._bar_string, end="\r", flush=True)
    
    def end(self):
        self._active_bar = False
        self.bar_cnt = 0
        self._time_bar = None
        self._max_length_bar = 0

        print("")

# returns a list of printable colors
def getcolors(docolors=True):
  colors = {
    "red": "",
    "yellow": "",
    "green": "",
    "bold": "",
    "blue": "",
    "purple": "",
    "reset": "",
    "underline": "",
    "supported": False
  }

  if not docolors:
    return colors
  
  elif os.name == "nt":
    try:
      colors["reset"] = colorama.Style.RESET_ALL
      colors["bold"] = colorama.Style.BRIGHT
      colors["green"] = colorama.Fore.GREEN
      colors["yellow"] = colorama.Fore.YELLOW
      colors["blue"] = colorama.Fore.CYAN
      colors["red"] = colorama.Fore.RED
      colors["purple"] = colorama.Fore.LIGHTBLUE_EX
      colors["underline"] = colorama.Style.UNDERLINE
      colors["supported"] = True
    except:
      pass
  else:
    colors["reset"] = "\033[00m"
    colors["bold"] = "\033[01m"
    colors["green"] = "\033[32m"
    colors["yellow"] = "\033[93m"
    colors["blue"] = "\033[96m"
    colors["red"] = "\033[31m"
    colors["purple"] = "\033[35m"
    colors["underline"] = "\033[04m"
    colors["supported"] = True

  return colors