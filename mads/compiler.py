from const import COMPILEROPTIONS, VERSION, REGEX
import utils

import re

class compiler(object):
    def __init__(self, tokenizer, options, logger):
        self.tokens = tokenizer.data
        self.lines = tokenizer.lines
        self.options = options
        self.logger = logger
        self.data = { }
        
        # track the fields for everything
        self.scene_types_fields = { }
        self.interaction_types_fields = { }

        self.scene_require = [ ]
        self.interaction_require = [ ]

        self.co = COMPILEROPTIONS.copy()

        self.refs = []

        self.STRINGFMT = re.compile(REGEX["STRINGFMT"])
    
    def i_find_refs(self):
        self.logger.log("compiler", "finding references", 3)
        for primary_scene in self.tokens:
            for secondary_scene in self.tokens[primary_scene]:
                if self.tokens[primary_scene][secondary_scene]["type"] == "config":
                    continue # do not add the .info refs 
                for interaction_name in self.tokens[primary_scene][secondary_scene]["interactions"]:
                    ref = primary_scene + "." + secondary_scene + "." + interaction_name
                    # do not need to check if the ref already exists
                    # as that is checked in the tokenizer
                    self.refs.append(ref)

    def i_fmt(self, string): # TODO: fill this in with string replacements
        for key, value in self.options.replacements.items():
            string = string.replace(key.lower() + "()", value)

        for key, value in self.options.flags.items():
            string = string.replace("mads." + key.lower() + "()", value)
        
        for not_found in self.STRINGFMT.findall(string):
            self.logger.log("compiler", "'" + not_found + "()' string replacement is not defined", 1)

        return string

    def i_parse_fields(self, fields, rv, types):
        current_fields = {}
        for field in fields:
            dbg = utils.dbg(self.logger, field["scope_tree"], field["scope_lines"], self.lines, field["file_name"])
            line_num = field["line_num"]

            # cannot have a key the same as the dialouge or options menus
            if field["id"] in (self.co["output.dialouge"], self.co["output.options"]):
                dbg.error("field error", "invalid field name", line_num)

            if field["id"] in current_fields:
                if field["id"] in types:
                    if types[field["id"]] == "value":
                        dbg.error("field error", "type of field does not match static type", line_num)
                    
                match (field["conditional"] != None, len(current_fields[field["id"]][1]) != 0):
                    case (True, True): # already set as conditional and currently conditional
                        if field["id"] in types:
                            if types[field["id"]] != "conditional":
                                dbg.error("field error", "type of field does not match static type", line_num)

                        current_fields[field["id"]][0].append(field["value"])
                        current_fields[field["id"]][1].append(field["conditional"])
                        current_fields[field["id"]][2] = "conditional"
                    case (False, False): # not a conditional and was never a conditional
                        if field["id"] in types:
                            if types[field["id"]] != "list":
                                dbg.error("field error", "type of field does not match static type", line_num)

                        current_fields[field["id"]][0].append(field["value"])
                        current_fields[field["id"]][2] = "list"
                    case (_, _):
                        dbg.error("field error", "type of field does not match static type", line_num)
            else:
                if field["conditional"] != None:
                    current_fields[field["id"]] = [
                        [field["value"]], # values
                        [field["conditional"]], # conditionals
                        "conditional" # type
                    ]
                else:
                    current_fields[field["id"]] = [
                        [field["value"]], # values
                        [], # conditionals
                        "value" # type
                    ]

        for field_id in current_fields:
            field = current_fields[field_id]
            if field[2] == "value":
                rv[field_id] = field[0][0]
            elif field[2] == "list":
                rv[field_id] = field[0]
            elif field[2] == "conditional":
                rv[field_id] = []
                for value, condition in zip(field[0], field[1]):
                    rv[field_id].append([condition, value])

        return rv

    def i_parse_ref(self, primary_scene, secondary_scene, ref, line_num, scope_tree, scope_lines, file_name):
        end_ref = ""
        full_ref = ""
        dbg = utils.dbg(self.logger, scope_tree, scope_lines, self.lines, file_name)

        if ref.startswith("$."):
            if len(ref[2:]) == 0:
                dbg.error("reference error", "invalid local reference format", line_num)

            full_ref = primary_scene + "." + secondary_scene + "." + ref[2:]
            if self.options.support["full-ref"]:
                end_ref = primary_scene + "." +  secondary_scene + "." + ref[2:]
            else:
                end_ref = ref[2:]
        else:
            # allow full refs if they are in the current scene
            if ref.startswith(primary_scene + "." + secondary_scene + "."):
                end_ref = '.'.join(ref.split(".")[2:])
                full_ref = ref
            elif self.options.support["full-ref"]:
                if len(ref.split(".")) >= 3:
                    end_ref = ref
                    full_ref = ref
                else:
                    dbg.error("reference error", "invalid full reference format", line_num)
            else:
                dbg.error("reference error", "mads file does not support full-ref", line_num)

        if full_ref in self.refs:
            return end_ref
        else:
            dbg.error("reference error", "reference does not exist", line_num)
    
    def i_parse_interaction(self, interaction, primary_scene, secondary_scene):
        current_interactions = self.i_parse_fields(interaction["fields"], {}, self.interaction_types_fields)

        current_interactions[self.co["output.options"]] = []
        current_interactions[self.co["output.dialouge"]] = []

        for option in interaction["options"]:
            current_interactions[self.co["output.options"]].append([
                option["conditional"],
                {
                    self.co["output.options.ref"]: self.i_parse_ref(primary_scene, secondary_scene,
                                                                    option["ref"],
                                                                    option["line_num"],
                                                                    option["scope_tree"],
                                                                    option["scope_lines"],
                                                                    option["file_name"]),
                    self.co["output.options.text"]: self.i_fmt(option["text"])
                }
            ])
        
        for dialouge in interaction["dialouge"]:
            current_interactions[self.co["output.dialouge"]].append([])
            for line in dialouge["texts"]:
                current_interactions[self.co["output.dialouge"]][-1].append(self.i_fmt(line))
        
        return current_interactions

    def i_parse_info_fields(self, fields):
        rv = {}
        for field in fields:
            if field["id"] in rv:
                rv[field["id"]]["scope_lines"].append(field["scope_lines"])
                rv[field["id"]]["scope_tree"].append(field["scope_tree"])
                rv[field["id"]]["line_num"].append(field["line_num"])
                rv[field["id"]]["values"].append(field["line_num"])
                rv[field["id"]]["conditionals"].append(field["conditional"])
            else:
                rv[field["id"]] = {
                    "split": field["id"].split("."),
                    "scope_lines": [field["scope_lines"]],
                    "scope_trees": [field["scope_tree"]],
                    "line_nums": [field["line_num"]],
                    "values": [field["value"]],
                    "conditionals": [field["conditional"]],
                    "file_name": field["file_name"]
                }
        return rv

    def i_parse_info_primary(self, field):
        if field == "version":
            v = utils.try_type(field["values"][-1], float)
            dbg = utils.dbg(self.logger, field["scope_trees"][-1]
                            ,field["scope_lines"][-1]
                            ,self.lines
                            ,field["file_name"])
            if not v[0]: # failed conversion
                dbg.error("syntax error", "parameter must be a version", field["line_nums"][-1])
            elif v[1] <= VERSION:
                msg = "mads does not support version " + str(v[1])
                dbg.error("version error", msg, field["line_nums"][-1])
        elif field == "support":
            for value, condition, line_num, scope_tree, scope_lines in zip(field["values"]
                                                                           ,field["conditionals"]
                                                                           ,field["line_nums"]
                                                                           ,field["scope_trees"]
                                                                           ,field["scope_lines"]):
                if value in self.options.support:
                    self.options.support[value] = True if condition == None else condition
                else:
                    dbg = utils.dbg(self.logger, scope_tree, scope_lines, self.lines, field["file_name"])
                    msg = "mads does not support " + value
                    dbg.error("support error", msg, line_num)
    
    # function uses 'tag' as it is for both interactions
    # and scenes
    def i_check_required(self, tag_obj, required, tag_type):
        fields = [i["id"] for i in tag_obj["fields"]]
        for required_field in required:
            if not required_field in fields:
                dbg = utils.dbg(self.logger
                                ,tag_obj["scope_tree"]
                                ,tag_obj["scope_lines"]
                                ,self.lines
                                ,tag_obj["file_name"])
                dbg.error("requirement error", "field '" + required_field + "' does not exist in " + tag_type
                            ,tag_obj["line_num"])

    def i_parse_required(self):
        self.logger.log("compiler", "resolving required fields", 3)
        for primary_scene in self.tokens:
            for secondary_scene in self.tokens[primary_scene]:
                scene = self.tokens[primary_scene][secondary_scene]
                if scene["type"] == "scene":
                    self.i_check_required(scene, self.scene_require, "scene")
                    for interaction_name in scene["interactions"]:
                        interaction = scene["interactions"][interaction_name]
                        self.i_check_required(interaction, self.interaction_require, "interaction")

    def parse(self):
        self.i_find_refs()

        # find the number of scenes
        cnt = 0
        for i in self.tokens:
            for p in self.tokens[i]:
                cnt += 1
        self.logger.bar_max = cnt

        for primary_scene in self.tokens:
            if not primary_scene in self.data:
                if primary_scene != "":
                    self.data[primary_scene] = { } # create the primary scene

            for secondary_scene in self.tokens[primary_scene]:
                self.logger.next("parsing scenes")
                scene = self.tokens[primary_scene][secondary_scene]

                if scene["type"] == "config": # if .info configuration
                    self.logger.log("compiler", "compiling configuration", 3)
                    primary_fields = self.i_parse_info_fields(scene["fields"])
                    for field in primary_fields:
                        self.i_parse_info_primary(field)

                    for interaction in scene["interactions"]:
                        interaction_fields = self.i_parse_info_fields(scene["interactions"][interaction]["fields"])
                        # the tokenizer checks to make sure 
                        # it is a valid interaction
                        for field_name in interaction_fields:
                            field = interaction_fields[field_name]
                            dbg = utils.dbg(self.logger, field["scope_trees"][-1]
                                            ,field["scope_lines"][-1]
                                            ,self.lines
                                            ,field["file_name"])
                                            
                            match [interaction,  *field["split"]]:
                                case ["declare.scene", "field", "require"]:
                                    self.scene_require.append(field["values"][-1])
                                case ["declare.interaction", "field", "require"]:
                                    self.interaction_require.append(field["values"][-1])
                                case [_, "field", "require"]:
                                    dbg.error("name error", "incorrect location for require", field["line_nums"][-1])
                                case ["declare.scene"|"declare.interaction", "field", "types", x]:
                                    self.scene_types_fields[x] = field["values"][-1]
                                case [_, "field", "types", _]:
                                    dbg.error("name error", "incorrect location for type definition", field["line_nums"][-1])
                                case ["compiler", *_]:
                                    if field_name in self.co:
                                        self.co[field_name] = field["values"][-1]
                                    else:
                                        dbg.error("name error", "compiler option does not exist", field["line_nums"][-1])
                                case [*_]:
                                    dbg.error("name error", "invalid option", field["line_nums"][-1])
                elif scene["type"] == "ref": # if reference
                    self.logger.log("compiler", "compiling reference " + scene["ref"], 4)
                    # create the secondary scene
                    self.data[primary_scene][secondary_scene] = self.i_parse_ref(primary_scene
                                                                                 ,secondary_scene
                                                                                 ,scene["ref"]
                                                                                 ,scene["line_num"]
                                                                                 ,[],[]
                                                                                 ,scene["file_name"])
                else:
                    self.logger.log("compiler", "compiling tag " + primary_scene + "." + secondary_scene, 4)
                    defualt = {
                        self.co["output.interactions"]: {},
                        self.co["output.options"]: {},
                        self.co["output.dialouge"]: {}
                    }
                    # create the secondary scene
                    self.data[primary_scene][secondary_scene] \
                            = self.i_parse_fields(scene["fields"], defualt, self.scene_types_fields)

                    for interaction_name in scene["interactions"]:
                        interaction_content = scene["interactions"][interaction_name]

                        self.data[primary_scene][secondary_scene][self.co["output.interactions"]][interaction_name] \
                            = self.i_parse_interaction(interaction_content, primary_scene, secondary_scene)
        
        self.logger.end()
        self.i_parse_required()