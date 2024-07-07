from const import REGEX, REGULAR_LINE, FILENAME_LINE
import utils as utils

import re
import os.path

def pre_error(error_type, error_message, line_num, virtual_line_num, lines, file, logger):
    c = logger.c
    prefix = c["red"] + c["bold"] + "preprocesser error " + c["reset"] + "in file " \
        + c["blue"] + "'" + file + "' on line " + str(virtual_line_num+1) + c["reset"]
    utils.simple_error(c["red"] + c["bold"] + error_type + c["reset"]
                       ,prefix
                       ,error_message
                       ,"  " + lines[line_num])

def parse_file(file_name):
    rv = 0
    content = ""
    try:
        file = open(file_name, "r")
        content = file.read().split("\n")
    except FileNotFoundError:
        rv = -1
    except IsADirectoryError:
        rv = -2
    
    return (rv, content)

class preprocesser(object):
    def __init__(self, parsed_lines, file_name, options, logger):
        self.lines = parsed_lines
        self.options = options
        self.logger = logger
        self.file_name = file_name
        self.import_files = [file_name]

        # for traceback errors
        self.return_lines = [(0, file_name, -1, FILENAME_LINE)]

        self.PREPROCESSER = re.compile(REGEX["PREPROCESSER"]+REGEX["COMMENT"])

    def _if(self):
        pass
    
    def _import(self, name, line_num, virtual_line_num):
        path = os.path.abspath(name)
        append_path = str(path)
        nice_file_name = name

        if path in self.import_files:
            pre_error("import error", "file " + name + " has already been imported"
                      ,line_num
                      ,virtual_line_num
                      ,self.lines
                      ,self.file_name
                      ,self.logger)
        else:
            self.logger.log("preprocessor", "starting import of '" + path + "'", 4)
            import_code, import_body = parse_file(path)
            # if it cant find it, check with a .mds extention
            if import_code != 0:
                append_path += ".mds"
                nice_file_name += ".mds"
                import_code, import_body = parse_file(path + ".mds")

            if import_code == -1:
                pre_error("file error", "file '" + name + "' does not exist"
                          ,line_num
                          ,virtual_line_num
                          ,self.lines
                          ,self.file_name
                          ,self.logger)
            elif import_code == -2:
                pre_error("file error", "path '" + name + "' is a directory"
                          ,line_num
                          ,virtual_line_num
                          ,self.lines
                          ,self.file_name
                          ,self.logger)

            self.import_files.append(append_path)
            first_name = self.file_name
            self.file_name = name

            # the comment is just a placeholder for debug purposes
            self.lines = self.lines[:line_num] \
                        + ["// file " + path + " was imported here"] \
                        + import_body \
                        + ["#mads:filename_change " + first_name + "|" + str(virtual_line_num)] \
                        + self.lines[line_num+1:]  \
            
            self.logger.log("preprocessor", "new file imported '" + name + "'", 3)

            return nice_file_name

    def parse(self):
        multicomment = False
        # the incrementor is at the start of the
        # while loop
        line_num = -1
        virtual_line_num = -1
        notify_inc = 24 # increment notify to 24 to leave room for future system

        while line_num+1 < len(self.lines):
            self.logger.bar_max = len(self.lines)
            self.logger.next("parsing lines")

            line_num += 1
            virtual_line_num += 1

            debug_object = (line_num, virtual_line_num, self.lines, self.file_name, self.logger)

            line = self.lines[line_num]
            if "\t" in line: # fail if using tabs
                pre_error("syntax error", "mads does not support tabs", *debug_object)
            indentation = len(line)-len(line.lstrip())

            line = line.lstrip()

            #if (todo_idx := line.find("//TODO:")) != -1:
            #    notify_inc += 1
            #    todo_text = "(" + f"{notify_inc:#0{6}x}" + ")" + line[todo_idx+7:]

            #    todo_text = todo_text.replace("<", self.logger.c["bold"]).replace(">", self.logger.c["reset"])
            #    self.logger.log("preprocessor", todo_text, -1)

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
                        file_name = self._import(x, line_num, virtual_line_num)
                        # need -1 will increment to zero on next run
                        # otherwise every import will bump line number
                        # by one line down
                        virtual_line_num = -1
                        self.return_lines.append((indentation, file_name, virtual_line_num, FILENAME_LINE))
                    case ("import", _, _):
                        pre_error("syntax error", "invalid format for #import", *debug_object)

                    case ("mads:filename_change", x, None):
                        value_split = x.split("|")
                        virtual_line_num = int(value_split[-1])
                        self.file_name = "|".join(value_split[:-1])
                        self.return_lines.append((indentation, self.file_name, virtual_line_num, FILENAME_LINE))
                    case ("mads:filename_change", _, _):
                        pre_error("syntax error", "invalid internal command", *debug_object)
                    
                    case (_, _, _):
                        pre_error("syntax error", "invalid pound command", *debug_object)
                pass
            else:
                self.return_lines.append((indentation, line, virtual_line_num, REGULAR_LINE))

        self.logger.end()