import pre
import utils
import output
import compiler
import tokenizer
from const import VERSION, PROG_NAME, HELP_MENU

import argparse
import sys
import re
import os.path


def exit():
  sys.exit(0)

def error(text):
  print(PROG_NAME + ": error: " + text)
  exit()

def parsePositionals(args_obj, options):
  for positional in args_obj:
    if (match := re.match(r'(?P<key>\w+):(?P<value>.+)', positional)) != None:
      options.replacements[match.group("key")] = match.group("value")
    elif (match := re.match(r'(?P<key>\w+)=(?P<value>.+)', positional)) != None:
      options.flags[match.group("key")] = match.group("value")
    else:
      error("positional argument " + positional + " is invalid syntax")

def parseArgs(args_obj):
  do_compile = False
  options = utils.Options()

  parsePositionals(args_obj.positionals, options)

  if args_obj.version:
    print(PROG_NAME + " version " + str(VERSION))
    exit()

  if args_obj.help:
    print(HELP_MENU)
    print("builtin preprocessor flags:")
    for i in options.flags:
      print(" - " + i)
    exit()

  match (args_obj.input, args_obj.output, args_obj.console):
    case (None, None, None):
      error("no actionable arguments given")
    case (None, _, _):
      error("must have an --input command")
    case (_, None, None):
      error("must have either --output or --console")
    case (_, _, _):
      do_compile = True
    case (_, _, None):
      do_compile = True
    case (_, None, _):
      do_compile = True
  
  options.pretty = args_obj.pretty
  options.log_severity = args_obj.level
  options.end_format = args_obj.format
  options.segment = args_obj.segment
  options.boring = args_obj.boring
  options.notodo = args_obj.notodo

  log = utils.Logger(options.log_severity, 60, not options.boring)
  
  if do_compile:
    import_code, import_body = pre.parseFile(args_obj.input)
    if import_code == -1:
      error("file '" + args_obj.input + "' does not exist")
    elif import_code == -2:
      error("path '" + args_obj.input + "' is a directory")
    
    log.log("preprocessor", "starting", 2)
    
    preproc = pre.Preprocesser(import_body, args_obj.input, options, log)
    preproc.parse()

    log.log("tokenizer", "starting", 2)

    tokens = tokenizer.Tokenizer(preproc, options, log)
    tokens.parse()

    log.log("compiler", "starting", 2)

    compiled = compiler.Compiler(tokens, options, log)
    compiled.parse()

    log.log("output", "compiler", 2)

    output.dump(compiled, args_obj.output, options, log)
  

if __name__ == "__main__":
  args_parser = argparse.ArgumentParser(PROG_NAME, "usage of mads", add_help=False)

  args_parser.add_argument("--input", "-i", action="store")
  args_parser.add_argument("--console", "-c", action="store_true") # TODO: implement
  args_parser.add_argument("--output", "-o", action="store")

  args_parser.add_argument("--version", "-v" ,action='store_true')
  args_parser.add_argument("--help", "-h", action="store_true")

  args_parser.add_argument("--segment", "-S", action="store_true")
  args_parser.add_argument("--pretty", "-p", action="store_true")
  args_parser.add_argument("--boring", "-B", action="store_true")
  args_parser.add_argument("--silent", "-Q", action="store_true") # TODO: implement

  args_parser.add_argument("--notodo", "-T", action="store_true")
  args_parser.add_argument("--format", "-f", action="store", choices=["json", "pickle", "xml"], default="json")
  args_parser.add_argument("--level", "-l", action="store", choices=[0, 1, 2, 3, 4], default=2, type=int)

  args_parser.add_argument('positionals', metavar='N', type=str, nargs='*')

  args = args_parser.parse_args()

  parseArgs(args)
