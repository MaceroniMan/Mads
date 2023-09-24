import os
import sys
import uuid
import time

def simple_error(error_type, error_prefix, error_message, error_body):

    print(error_prefix)
    print(error_body)
    print(error_type + " : " + error_message)

    sys.exit(1)

def make_uuid():
    return str(uuid.uuid4())

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

class dbg(object):
    def __init__(self, scope_tree, scope_lines, lines, file_name):
        self.scope_tree = scope_tree
        self.scope_lines = scope_lines
        self.lines = lines
        self.file_name = file_name

    def error(self, error_type, error_text, line_obj):
        #prefix = "error in file '" + self.file_name + "' on line " + str(line_obj[0]+1) + " with scope:"
        prefix = "traceback (most recent scope change last):"
        
        prev_scope = "<main>"
        for scope_name, scope_line in zip(self.scope_tree, self.scope_lines):
            prefix += "\n  file '" + self.file_name + "' line " + str(scope_line[0]+1) + " in " + prev_scope
            prefix += "\n    " + self.lines[scope_line[1]][1]
            prev_scope = scope_name
        
        body = "  file '" + self.file_name + "' line " + str(line_obj[0]+1) + " in " + prev_scope
        body += "\n    " + self.lines[line_obj[1]][1]
        body += "\n    " + "^"*len(self.lines[line_obj[1]][1])

        simple_error(error_type, prefix, error_text, body)

# contains the configuration application-wide
class options(object):
    def __init__(self):
        self.log_severity = 1
        self.end_format = "json"
        self.pretty = False
        self.force = False
        self.segment = False
        
        self.cwd = os.getcwd()

        self.replacements = {}

        self.flags = {
            "COS": "WINDOWS" if os.name == "nt" else "POSIX",
            "CTIME": time.strftime('%X %x %Z'),
            "CWD": self.cwd
        }

        self.support = {
           "full-ref": False,
           "scene-ref": True
        }

    # severity:
    # 1: major milestones
    # 2: minor milestones
    # 3: debug messages
    def log(self, log_type, log_text, log_severity):
        maximum_length = len("preprocessor")
        if log_severity <= self.log_severity:
            log_type_msg = log_type + " "*(maximum_length-len(log_type))
            print("[ " + str(round(time.time()*1000)) + "ms ] " + log_type_msg, ":" + " "*log_severity + log_text)