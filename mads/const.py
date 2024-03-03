COMPILEROPTIONS = { # compiler options
    "output.interactions": "interactions",
    "output.dialouge": "dialouge",
    "output.options": "options",

    "output.options.ref": "ref",
    "output.options.text": "text",

    "output.exit": "exit",
    "output.noconditional": "true"
}

REGEX = {
    "TAG": r'\[(?P<id>(\w|-|\.)+)\](\s*->\s*(?P<ref>(\.|\w|-)+))?',
    "FIELD_UNQUOTE": r'\*\s*(?P<id>(\w|\.|-)+):\s*(?P<value>(\w|\.|-|\$)+)(\s*{\s*(?P<conditional>.*)\s*})?',
    "FIELD_QUOTE": r'\*\s*(?P<id>(\w|\.|-)+):\s*("(?P<value>.*)")(\s*{\s*(?P<conditional>.*)\s*})?',
    "DIALOUGE": r'\?\s*(?P<text>".*")',
    "OPTION": r'>\s*"(?P<text>.*)"\s*(?P<ref>(\$\.|\.|-|\w)+)(\s*{\s*(?P<conditional>.*)\s*})?',
    "ADHOC": r':\s*"(?P<text>.*)"\s*(\[(?P<id>(\w|-|\.)+)\])?(\s*{\s*(?P<conditional>.*)\s*})?',

    "DIALOUGE_QUOTES": r'(?:[^\s,"]|"(?:\\.|[^"])*")+',
    "COMMENT": r'(\s*\/\/.*)*\s*$',

    "PREPROCESSER": r'#\s*(?P<command>(mads:)?\w+)\s*(?P<argument>[\w|\.|\\|/]+)?\s*({(?P<conditional>.*)})?',

    "STRINGFMT": r'(?P<command>[\w\.]+)\(\)'
}

REGULAR_LINE = "reg"
FILENAME_LINE = "file"

CONFIGURATION_NAME = "info"

VERSION = 1.0
PROG_NAME = "mads"
HELP_MENU = """
usage: mads -i INPUT -o OUTPUT [-h] [-L] [-S] [-p] [-Q] [-B] [-f {json, xml}] [-l {0, 1, 2, 3, 4}] [-t {windows, linux}] [key:value ...] [flag=value ...]

mads, a dialouge script

required arguments:
  -i, --input INPUT .... define the entrypoint for the compiler (a .mds file)
  -o, --output OUTPUT .. define the output file

optional arguments
  -h, --help ................... show this help menu and exit
  -v, --version ................ show version information and exit
  -S, --segment ................ split up the output files by primary scene
  -p, --pretty ................. pretty-print the output json or xml file
  -Q, --quiet .................. suppress all output (except loading bar)
  -B, --boring ................. suppress all colors and fancy characters
  -f, --format {json, pickle} .. tell the compiler what the output format should be (default is json)
  -l, --level {0, 1, 2, 3, 4} .. define the logging level (default is 2)

positional arguments:
  key:value ... will add a key-value pair to the replacement map
  flag=value .. will set a preprocesser flag to value, defines a flag
"""

FLAGS_HELP = {
  "COS" : "the operating system mads is running on",
  "CTIME" : "start time of compile",
  "CWD" : "working directory of project"
}