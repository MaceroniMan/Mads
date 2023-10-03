from const import REGEX, FILENAME_LINE, CONFIGURATION_NAME
import utils

import re

class tokenizer(object):
    def __init__(self, preprocesser, options, logger):
        self.lines = preprocesser.return_lines
        self.options = options
        self.logger = logger

        self.data = { }
        self.file_name = ""
        # out of all, out of just file
        self.line_num = (0, 0)

        self.scope_lines = []
        self.scope_tree = []

        self.scene = ["", ""]

        self.indentation_tree = []
        self.next_indent = False

        self.config_done = False # already done parsing .info
        self.do_config = False # currently in the .info

        self.TAG = re.compile(REGEX["TAG"]+REGEX["COMMENT"])
        self.FIELD_UNQUOTE = re.compile(REGEX["FIELD_UNQUOTE"]+REGEX["COMMENT"])
        self.FIELD_QUOTE = re.compile(REGEX["FIELD_QUOTE"]+REGEX["COMMENT"])
        self.DIALOUGE = re.compile(REGEX["DIALOUGE"]+REGEX["COMMENT"])
        self.OPTION = re.compile(REGEX["OPTION"]+REGEX["COMMENT"])
        self.ADHOC = re.compile(REGEX["ADHOC"]+REGEX["COMMENT"])
        self.DIALOUGE_QUOTES = re.compile(REGEX["DIALOUGE_QUOTES"]+REGEX["COMMENT"])
        self.PREPROCESSER = re.compile(REGEX["PREPROCESSER"]+REGEX["COMMENT"])
    
    def i_make_tag(self, npc_id, secondary_scene, value):
        # return values:
        # 1: aux already exists
        # 0: success

        make_secondary_scene = False
        make_id = False
        if npc_id in self.data:
            if secondary_scene in self.data[npc_id]:
                return 1
            else:
                make_secondary_scene = True
        else:
            make_id = True
            make_secondary_scene = True
        
        if make_id:
            self.data[npc_id] = {}
        if make_secondary_scene:
            self.data[npc_id][secondary_scene] = value
        
        return 0

    def i_make_interaction(self, npc_id, secondary_scene, name, dbg_items):
        # return values:
        # 1: name already exists
        # 0: success

        if name in self.data[npc_id][secondary_scene]["interactions"]:
            return 1
        else:
            new_interaction = dbg_items | {"dialouge": [], "options": [], "fields" : []}

            self.data[npc_id][secondary_scene]["interactions"][name] = new_interaction
        
        return 0

    def i_check_indent(self, indentation):
        if indentation == 0: # top level tag
            # reset all scope
            self.scope_tree = []
            self.indentation_tree = []
            self.scope_lines = []

            return -1
        else:
            try:
                # find the current indent level
                current_indent = self.indentation_tree.index(indentation)
            except ValueError:
                dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                dbg.error("indentation error", "invalid indentation", self.line_num)

            self.scope_tree = self.scope_tree[:current_indent+1]
            self.indentation_tree = self.indentation_tree[:current_indent+1]
            self.scope_lines = self.scope_lines[:current_indent+1]
            
            return current_indent
    
    def i_split_scene(self, id):
        split_items = id.split(".")
        non_blank_items = []

        if split_items == ["", CONFIGURATION_NAME]: # if its a configuration menu
            return "", CONFIGURATION_NAME
        else:
            for i in split_items:
                if i != "":
                    non_blank_items.append(i)

            if len(non_blank_items) >= 2:
                return non_blank_items[0], ".".join(non_blank_items[1:])
            else:
                dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines)
                dbg.error("syntax error", "invalid scene definition", self.line_num)
    
    def _tag(self, match, indentation):
        m_id = match.group("id")
        m_ref = match.group("ref")

        current_indent = self.i_check_indent(indentation)
        
        if current_indent == -1: # top level tag, defines a whole interaction menu
            dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
            primary_scene, secondary_scene = self.i_split_scene(m_id)
            self.do_config = False

            if primary_scene == "" and secondary_scene == CONFIGURATION_NAME:
                if self.config_done: # if there has already been a .info
                    dbg.error("syntax error", "only one .info allowed", self.line_num)
                else:
                    # start def settings
                    self.do_config = True
                    self.config_done = True

            if m_ref != None:
                if self.do_config:
                    dbg.error("syntax error", ".info cannot be a reference", self.line_num)

                # make a new reference interaction
                rv = self.i_make_tag(primary_scene, secondary_scene, {
                    "type" : "ref",
                    "ref": m_ref,

                    "line_num": self.line_num,
                    "scope_lines": self.scope_lines.copy(),
                    "scope_tree": self.scope_tree.copy(),
                    "file_name": self.file_name
                })
                if rv == 1:
                    utils.error("syntax error", "scene already exists", self.line_num, dbg)
                
                self.scene = ["", ""]

            else:
                # make a new interaction menu
                rv = self.i_make_tag(primary_scene, secondary_scene, {
                    "type" : "config" if self.do_config else "scene",
                    "interactions" : {},
                    "fields" : [],

                    "line_num": self.line_num,
                    "scope_lines": self.scope_lines.copy(),
                    "scope_tree": self.scope_tree.copy(),
                    "file_name": self.file_name
                })
                if rv == 1:
                    dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                    dbg.error("syntax error", "scene already exists", self.line_num)

                self.scene = [primary_scene, secondary_scene]

                self.scope_tree.append(m_id)
                self.scope_lines.append(self.line_num)

                self.next_indent = True # the next line will run the indent operation
            
        elif current_indent == 0: # the start of a interaction menu
            if m_ref != None:
                dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                dbg.error("syntax error", "cannot have a scene reference here", self.line_num)

            if len(self.scope_tree) != 1: # not the first element in the menu
                self.scope_tree = [self.scope_tree[0]]
                self.scope_lines = [self.scope_lines[0]]
                self.indentation_tree = [self.indentation_tree[0]]
            
            if self.do_config:
                if not m_id in ["declare.scene", "declare.interaction", "compiler"]:
                    dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                    dbg.error("name error", m_id + " is not allowed here", self.line_num)

            rv = self.i_make_interaction(self.scene[0], self.scene[1], m_id, {
                "line_num": self.line_num,
                "scope_lines": self.scope_lines.copy(),
                "scope_tree": self.scope_tree.copy(),
                "file_name": self.file_name
            })
            if rv == 1:
                dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                dbg.error("syntax error", "dialouge already exists", self.line_num)
            
            self.scope_tree.append(m_id)
            self.scope_lines.append(self.line_num)
            self.next_indent = True # the next line will run the indent operation

            self.dialouge_id = m_id

        else:
            dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
            # tag exists somewhere it is not supposed to
            dbg.error("syntax error", "cannot defign a interaction here", self.line_num)

    def _field(self, match, indentation):
        m_id = match.group("id")
        m_ref = match.group("value")
        m_condid = match.group("conditional")

        current_indent = self.i_check_indent(indentation)

        if current_indent >= 1: # field inside of a dialouge
            self.data[self.scene[0]][self.scene[1]]["interactions"][self.scope_tree[current_indent]]["fields"].append({
                "id": m_id,
                "value": m_ref,
                "conditional": m_condid,
                "line_num": self.line_num,
                "scope_lines": self.scope_lines.copy(),
                "scope_tree": self.scope_tree.copy(),
                "file_name": self.file_name
            })
        elif current_indent == 0: # field inside of a dialouge menu
            self.data[self.scene[0]][self.scene[1]]["fields"].append({
                "id": m_id,
                "value": m_ref,
                "conditional": m_condid,
                "line_num": self.line_num,
                "scope_lines": self.scope_lines.copy(),
                "scope_tree": self.scope_tree.copy(),
                "file_name": self.file_name
            })
        else:
            dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
            dbg.error("syntax error", "invalid location for a data field", self.line_num)

    def _adhoc(self, match, indentation):
        m_text = match.group("text")
        m_id = match.group("id")
        m_condid = match.group("conditional")

        current_indent = self.i_check_indent(indentation)

        if current_indent >= 1: # field inside of a dialouge
            if m_id == None:
                m_id = utils.make_uuid()

            rv = self.i_make_interaction(self.scene[0], self.scene[1], m_id, {
                "line_num": self.line_num,
                "scope_lines": self.scope_lines.copy(),
                "scope_tree": self.scope_tree.copy(),
                "file_name": self.file_name
            })

            if rv == 1:
                dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                dbg.error("syntax error", "interaction already exists", self.line_num)
            
            self.data[self.scene[0]][self.scene[1]]["interactions"][self.scope_tree[current_indent]]["options"].append({
                "text": m_text,
                "ref": "$." + m_id,
                "conditional": m_condid,
                "line_num": self.line_num,
                "scope_lines": self.scope_lines.copy(),
                "scope_tree": self.scope_tree.copy(),
                "file_name": self.file_name
            })

            self.scope_tree.append(m_id)
            self.scope_lines.append(self.line_num)
            self.next_indent = True # the next line will run the indent operation

        else:
            dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
            dbg.error("syntax error", "invalid location for a adhoc option", self.line_num)

    def _option(self, match, indentation):
        m_text = match.group("text")
        m_ref = match.group("ref")
        m_condid = match.group("conditional")

        current_indent = self.i_check_indent(indentation)

        if current_indent >= 1: # field inside of a dialouge

            self.data[self.scene[0]][self.scene[1]]["interactions"][self.scope_tree[current_indent]]["options"].append({
                "text": m_text,
                "ref": m_ref,
                "conditional": m_condid,
                "line_num": self.line_num,
                "scope_lines": self.scope_lines.copy(),
                "scope_tree": self.scope_tree.copy(),
                "file_name": self.file_name
            })

        else:
            dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
            dbg.error("syntax error", "invalid location for a adhoc option", self.line_num)

    def _dialouge(self, match, indentation):
        m_text = match.group("text")

        current_indent = self.i_check_indent(indentation)

        if current_indent >= 1: # field inside of a dialouge

            self.data[self.scene[0]][self.scene[1]]["interactions"][self.scope_tree[current_indent]]["dialouge"].append({
                "texts": utils.parse_string(m_text),
                "line_num": self.line_num,
                "scope_lines": self.scope_lines.copy(),
                "scope_tree": self.scope_tree.copy(),
                "file_name": self.file_name
            })

        else:
            dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
            dbg.error("syntax error", "invalid location for a dialouge line", self.line_num)

    def parse(self):
        self.logger.bar_max = len(self.lines)

        for total_line_num, line_obj in enumerate(self.lines):
            self.logger.next("tokenizing lines")
            indentation = line_obj[0]
            line = line_obj[1]
            self.line_num = (line_obj[2], total_line_num)

            if line_obj[3] == FILENAME_LINE:
                self.logger.log("tokenizer", "switching file to '" + line + "'", 3)
                self.file_name = line
            else:
                if self.next_indent:
                    if len(self.indentation_tree) >= 1:
                        if self.indentation_tree[-1] >= indentation:
                            dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                            dbg.error("indentation error", "line must be indented", self.line_num)
                    self.indentation_tree.append(indentation)
                    self.next_indent = False

                if (match := self.TAG.match(line)) != None:
                    self._tag(match, indentation)
                elif (match := self.FIELD_UNQUOTE.match(line)) != None:
                    self._field(match, indentation)
                elif (match := self.FIELD_QUOTE.match(line)) != None:
                    self._field(match, indentation)
                elif (match := self.ADHOC.match(line)) != None:
                    if self.do_config:
                        dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                        dbg.error("syntax error", "not allowed inside of .info")
                    else:
                        self._adhoc(match, indentation)
                elif (match := self.DIALOUGE.match(line)) != None:
                    if self.do_config:
                        dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                        dbg.error("syntax error", "not allowed inside of .info")
                    else:
                        self._dialouge(match, indentation)
                elif (match := self.OPTION.match(line)) != None:
                    if self.do_config:
                        dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                        dbg.error("syntax error", "not allowed inside of .info", self.line_num)
                    else:
                        self._option(match, indentation)
                else:
                    dbg = utils.dbg(self.logger, self.scope_tree, self.scope_lines, self.lines, self.file_name)
                    dbg.error("syntax error", "malformed line", self.line_num)
                    
        self.logger.end()