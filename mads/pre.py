from const import REGEX, REGULAR_LINE, FILENAME_LINE
import utils as utils

import re, time

def pre_error(error_type, error_message, line_num, lines, file):
    prefix = "preprocesser error in file '" + file + "' on line " + str(line_num+1)
    utils.simple_error(error_type, prefix, error_message, "  " + lines[line_num])

def parse_file(file_name):
    rv = 0
    try:
        file = open(file_name, "r")
        rv = file.read().split("\n")
    except FileNotFoundError:
        rv = 0

    if not rv:
        try:
            file = open(file_name+".mds", "r")
            rv = file.read().split("\n")
        except FileNotFoundError:
            rv = 0
    
    return rv

class preprocesser(object):
    def __init__(self, parsed_lines, file_name, options, logger):
        self.lines = parsed_lines
        self.options = options
        self.logger = logger
        self.file_name = file_name
        self.import_files = [file_name]

        self.return_lines = [(0, file_name, -1, FILENAME_LINE)]

        self.PREPROCESSER = re.compile(REGEX["PREPROCESSER"]+REGEX["COMMENT"])

    def _if(self):
        pass
    
    def _import(self, path, line_num):
        if path in self.import_files:
            pre_error("import error", "cannot import a file that has already been imported"
                      ,line_num
                      ,self.lines
                      ,self.file_name)
        else:
            self.logger.log("preprocessor", "new file imported '" + path + "'", 2)
            new_file_body = parse_file(path)
            if new_file_body == 0:
                pre_error("file error", "file '" + path + "' does not exist"
                          ,line_num
                          ,self.lines
                          ,self.file_name)

            self.import_files.append(path)
            first_name = self.file_name
            self.file_name = path

            # the comment is just a placeholder for debug purposes
            self.lines = self.lines[:line_num] + ["// file " + path + " was imported here"] \
                + new_file_body + ["#internal_change_filename " + first_name] + self.lines[line_num+1:]
            
            return path

    def parse(self):
        multicomment = False
        line_num = -1
        virtual_line_num = -1

        while line_num+1 < len(self.lines):
            self.logger.bar_max = len(self.lines)
            self.logger.next("parsing lines")

            line_num += 1
            virtual_line_num += 1

            line = self.lines[line_num]
            indentation = len(line)-len(line.lstrip())

            line = line.lstrip()

            if multicomment:
                if line.startswith("//~"):
                    multicomment = False
                    continue
                else:
                    continue
            elif line.startswith("//~"):
                multicomment = True
                continue
            elif line.strip() == "" or line.startswith("//"):
                continue
            
            if (match := self.PREPROCESSER.match(line)) != None:
                match (match.group("command"), match.group("argument"), match.group("conditional")):
                    case ("endif", None, None):
                        print("endif")
                    case ("endif", _, _):
                        pre_error("syntax error", "invalid format for #endif", line_num, self.lines, self.file_name)

                    case ("if", None, x):
                        print("if", x)
                    case ("if", x, None):
                        print("ifdef", x)
                    case ("if", _, _):
                        pre_error("syntax error", "invalid format for #if", line_num, self.lines, self.file_name)

                    case ("def", x, None):
                        print("def", x)
                    case ("def", _, _):
                        pre_error("syntax error", "invalid format for #def", line_num, self.lines, self.file_name)

                    case ("undef", x, None):
                        print("undef", x)
                    case ("undef", _, _):
                        pre_error("syntax error", "invalid format for #undef", line_num, self.lines, self.file_name)
                    
                    case ("import", x, None):
                        file_line = self._import(x, line_num)
                        virtual_line_num = 0
                        self.return_lines.append((indentation, file_line, virtual_line_num, FILENAME_LINE))
                    case ("import", _, _):
                        pre_error("syntax error", "invalid format for #import", line_num, self.lines, self.file_name)

                    case ("internal_change_filename", x, None):
                        virtual_line_num = 0
                        self.file_name = x
                        self.return_lines.append((indentation, x, virtual_line_num, FILENAME_LINE))
                    case ("internal_change_filename", _, _):
                        pre_error("syntax error", "invalid internal command", line_num, self.lines, self.file_name)
                    
                    case (_, _, _):
                        pre_error("syntax error", "invalid pound command", line_num, self.lines, self.file_name)
                pass
            else:
                self.return_lines.append((indentation, line, virtual_line_num, REGULAR_LINE))

        self.logger.end()