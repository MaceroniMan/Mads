import pre, tokenizer, utils, output, compiler
from const import VERSION, PROG_NAME, HELP_MENU

import argparse
import sys
import re

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
  options = utils.options()

  parsePositionals(args_obj.positionals, options)

  if args_obj.version:
    print(PROG_NAME + " version " + str(VERSION))
    exit()

  if args_obj.help:
    print(HELP_MENU)
    exit()

  match (args_obj.input, args_obj.output):
    case (None, None):
      error("no actionable arguments given")
    case (None, _):
      error("must have both --input and --output")
    case (_, None):
      error("must have both --input and --output")
    case (_, _):
      do_compile = True
  
  options.pretty = args_obj.pretty
  options.log_severity = args_obj.level
  options.end_format = args_obj.format
  options.segment = args_obj.segment
  options.boring = args_obj.boring

  log = utils.logger(options.log_severity, 60, not options.boring)
  
  if do_compile:
    starting_file = pre.parse_file(args_obj.input)
    if starting_file == 0:
      error("file '" + args_obj.input + "' does not exist")
    
    log.log("preprocessor", "starting", 2)
    
    preproc = pre.preprocesser(starting_file, args_obj.input, options, log)
    preproc.parse()

    log.log("tokenizer", "starting", 2)

    tokens = tokenizer.tokenizer(preproc, options, log)
    tokens.parse()

    log.log("compiler", "starting", 2)

    compiled = compiler.compiler(tokens, options, log)
    compiled.parse()

    log.log("output", "compiler", 2)

    output.dump(compiled, args_obj.output, options, log)
  

if __name__ == "__main__":
  args_parser = argparse.ArgumentParser(PROG_NAME, "usage of mads", add_help=False)

  args_parser.add_argument("--input", "-i", action="store")
  args_parser.add_argument("--output", "-o", action="store")

  args_parser.add_argument('--version', action='store_true')
  args_parser.add_argument("--help", "-h", action="store_true")

  args_parser.add_argument("--segment", "-S", action="store_true")
  args_parser.add_argument("--pretty", "-p", action="store_true")
  args_parser.add_argument("--quiet", "-Q", action="store_true")
  args_parser.add_argument("--boring", "-B", action="store_true")

  args_parser.add_argument("--format", "-f", action="store", choices=["json", "pickle"], default="json")
  args_parser.add_argument("--level", "-l", action="store", choices=[0, 1, 2, 3, 4], default=2, type=int)

  args_parser.add_argument('positionals', metavar='N', type=str, nargs='*')

  args = args_parser.parse_args()

  parseArgs(args)