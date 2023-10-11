from const import REGEX, REGULAR_LINE, FILENAME_LINE
import utils as utils

import re, time

def pre_error(error_type, error_message, line_num, lines, file, logger):
    c = logger.c
    prefix = c["red"] + c["bold"] + "preprocesser error " + c["reset"] + "in file " \
        + c["blue"] + "'" + file + "' on line " + str(line_num+1) + c["reset"]
    utils.simple_error(c["red"] + c["bold"] + error_type + c["reset"]
                       ,prefix
                       ,error_message
                       ,"  " + lines[line_num])

def parse_file(file_name):
    rv = 0
    try:
        file = open(file_name, "r")
        rv = file.read().split("\n")
    except FileNotFoundError:
        rv = 0
    except IsADirectoryError:
        rv = -1

    if not rv:
        try:
            file = open(file_name+".mds", "r")
            rv = file.read().split("\n")
        except FileNotFoundError:
            rv = 0
        except IsADirectoryError:
            rv = -1
    
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
                      ,self.file_name
                      ,self.logger)
        else:
            self.logger.log("preprocessor", "new file imported '" + path + "'", 2)
            new_file_body = parse_file(path)
            if new_file_body == 0:
                pre_error("file error", "file '" + path + "' does not exist"
                          ,line_num
                          ,self.lines
                          ,self.file_name
                          ,self.logger)
            if new_file_body == -1:
                pre_error("file error", "path '" + path + "' is a directory"
                          ,line_num
                          ,self.lines
                          ,self.file_name
                          ,self.logger)

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

            debug_object = (line_num, self.lines, self.file_name, self.logger)

            line = self.lines[line_num]
            if "\t" in line: # fail if using tabs
                pre_error("syntax error", "mads does not support tabs", *debug_object)
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
                        pre_error("syntax error", "invalid format for #endif", *debug_object)

                    case ("if", None, x):
                        print("if", x)
                    case ("if", x, None):
                        print("ifdef", x)
                    case ("if", _, _):
                        pre_error("syntax error", "invalid format for #if", *debug_object)

                    case ("def", x, None):
                        print("def", x)
                    case ("def", _, _):
                        pre_error("syntax error", "invalid format for #def", *debug_object)

                    case ("undef", x, None):
                        print("undef", x)
                    case ("undef", _, _):
                        pre_error("syntax error", "invalid format for #undef", *debug_object)
                    
                    case ("import", x, None):
                        # need -1 will increment to zero on next run
                        # otherwise every import will bump line number
                        # by one line down
                        virtual_line_num = -1
                        file_line = self._import(x, line_num)
                        self.return_lines.append((indentation, file_line, virtual_line_num, FILENAME_LINE))
                    case ("import", _, _):
                        pre_error("syntax error", "invalid format for #import", *debug_object)

                    case ("internal_change_filename", x, None):
                        # need -1 will increment to zero on next run
                        # otherwise every import will bump line number
                        # by one line down
                        virtual_line_num = -1
                        self.file_name = x
                        self.return_lines.append((indentation, x, virtual_line_num, FILENAME_LINE))
                    case ("internal_change_filename", _, _):
                        pre_error("syntax error", "invalid internal command", *debug_object)
                    
                    case (_, _, _):
                        pre_error("syntax error", "invalid pound command", *debug_object)
                pass
            else:
                self.return_lines.append((indentation, line, virtual_line_num, REGULAR_LINE))

        self.logger.end()