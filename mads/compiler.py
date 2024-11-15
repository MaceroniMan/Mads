from const import COMPILEROPTIONS, VERSION, REGEX
import utils

import re
import difflib

class compiler(object):
    def __init__(self, tokenizer, options, logger):
        self.tokens = tokenizer.data
        self.lines = tokenizer.lines
        self.options = options
        self.logger = logger
        self.data = {}
        
        # track the fields for everything
        self.scene_types_fields = {}
        self.interaction_types_fields = {}

        self.scene_require = []
        self.interaction_require = []

        self.co = COMPILEROPTIONS.copy()

        self.interaction_refs = []
        self.scene_refs = []

        self.STRINGFMT = re.compile(REGEX["STRINGFMT"])
    
    def i_find_refs(self):
        self.logger.log("compiler", "finding references", 3)
        for primary_scene in self.tokens:
            for secondary_scene in self.tokens[primary_scene]:
                self.scene_refs.append(primary_scene + "." + secondary_scene)

                if self.tokens[primary_scene][secondary_scene]["type"] == "config":
                    continue # do not add the .info refs 
                if self.tokens[primary_scene][secondary_scene]["type"] == "ref":
                    continue # nor add in reference ids (TODO: why? maybe delete this)
                for interaction_name in self.tokens[primary_scene][secondary_scene]["interactions"]:
                    ref = primary_scene + "." + secondary_scene + "." + interaction_name
                    # do not need to check if the ref already exists
                    # as that is checked in the tokenizer
                    self.interaction_refs.append(ref)

    def i_fmt(self, string):
        for key, value in self.options.replacements.items():
            string = string.replace(key.lower() + "()", value)

        for key, value in self.options.flags.items():
            string = string.replace("mads." + key.lower() + "()", value)
        
        for not_found in self.STRINGFMT.findall(string):
            self.logger.log("compiler", "'" + not_found + "()' string replacement is not defined", 1)

        return string

    def i_parse_fields(self, fields, rv, types, primary_scene, secondary_scene, parent_name):
        self.logger.log("compiler", "parsing fields for " + parent_name, 4)
        current_fields = {}
        for field in fields:
            dbg = utils.dbg(self.logger, field["scope_tree"], field["scope_lines"], self.lines, field["file_name"])
            line_num = field["line_num"]

            # cannot have a key the same as any of the required items in output
            if field["id"] in (self.co["output.dialouge"], self.co["output.options"], self.co["output.interactions"]):
                dbg.error("field error", "invalid field name", line_num)
            
            field_value = ""
            # set the correct types
            if field["type"] == "reference-id":
                field_value = self.i_parse_ref(primary_scene, secondary_scene,
                                                                field["value"],
                                                                field["line_num"],
                                                                field["scope_tree"],
                                                                field["scope_lines"],
                                                                field["file_name"])
            elif field["type"] == "number":
                try:
                    field_value = int(field["value"])
                except ValueError:
                    dbg.error("field error", "invalid sytanx for a integer field", line_num)
            else:
                field_value = field["value"]

            
            # add the entrypoints field (from entrypoints syntax)
            if field["id"] == self.co["output.entrypoints"]:
                if field["conditional"] is not None: # entrypoints MUST BE a conditional
                    if field["type"] != "reference-id": # and must a reference id
                        dbg.error("field error", "as the predefined entrypoints field, '" + field["conditional"] + "' must be either a string or a reference id" , line_num)
                    # reference id is checked above
                    rv[self.co["output.entrypoints"]].insert(0, [field["conditional"], field_value])
                else:
                    dbg.error("field error", "as a predefined entrypoints field, '" + field["conditional"] + "' must be a conditional type" , line_num)

            elif field["id"] in current_fields:

                # TODO: re-implement typing system
                #if field["id"] in types:
                #    if types[field["id"]] == "value":
                #        dbg.error("field error", "type of field does not match static type", line_num)

                stored_field = current_fields[field["id"]]

                if stored_field[3] != field["type"]:
                    dbg.error("field error", "type of field does not match the previous type definitions", line_num)
                
                if stored_field[3] == "script":
                    dbg.error("field error", "a field with a type of 'script' cannot be a list", line_num)
                
                # does new field have a conditional, stored general type
                match (field["conditional"] is not None, stored_field[2]):
                    case (True, "conditional"): # already set as conditional
                        current_fields[field["id"]][0].append(field_value)
                        current_fields[field["id"]][1].append(field["conditional"])
                    case (True, "list"): # wants to be conditional but set as list
                        dbg.error("field error", "cannot intermix lists and conditional lists for the same field", line_num)
                    case (False, "value" | "list"): # does not want to be conditional and set as list or value
                        current_fields[field["id"]][0].append(field_value)
                        current_fields[field["id"]][2] = "list"
                
                """ # OLD CODE
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
                """
            else:
                if field["type"] == "script":
                    current_fields[field["id"]] = [
                        [field["conditional"]], # values
                        [], # conditionals
                        "value", # general type
                        "script" # value type
                    ]
                elif field["conditional"] != None:
                    current_fields[field["id"]] = [
                        [field_value], # values
                        [field["conditional"]], # conditionals
                        "conditional", # general type
                        field["type"] # value type
                    ]
                else:
                    current_fields[field["id"]] = [
                        [field_value], # values
                        [], # conditionals
                        "value", # general type
                        field["type"] # value type
                    ]

        self.logger.log("compiler", "writing fields " + parent_name, 4)
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

        # is a local ref
        if ref.startswith("$."):
            if len(ref[2:]) == 0:
                dbg.error("reference error", "invalid local reference format", line_num)

            full_ref = primary_scene + "." + secondary_scene + "." + ref[2:]
            if self.options.support["full-ref"]:
                end_ref = primary_scene + "." +  secondary_scene + "." + ref[2:]
            else:
                end_ref = ref[2:]
        else:
            # shortcut methods bypass all error checking
            if ref.startswith("mads.") and len(ref.split(".")) == 2:
                if ref == "mads.exit":
                    return self.co["output.exit"]
                else:
                    dbg.error("reference error", ref + " is not a valid shortcut", line_num)
            
            # if full ref format
            if len(ref.split(".")) >= 3:
                if self.options.support["full-ref"]:
                    end_ref = ref
                    full_ref = ref
                else:
                    # allow full refs if they are in the current scene
                    if ref.startswith(primary_scene + "." + secondary_scene + "."):
                        end_ref = '.'.join(ref.split(".")[2:])
                        full_ref = ref
                    else:
                        dbg.error("reference error", "mads file does not support full-ref", line_num)
            else:
                dbg.error("syntax error", "unrecognized reference format '" + ref + "'", line_num)

        if full_ref in self.interaction_refs:
            return end_ref
        else:
            dbg.error("reference error", "reference '" + full_ref + "' does not exist", line_num)
    
    def i_parse_interaction(self, interaction, primary_scene, secondary_scene):
        interaction_name = ".".join(interaction["scope_tree"])
        current_interactions = self.i_parse_fields(interaction["fields"], {}, self.interaction_types_fields,
                                                   primary_scene,
                                                   secondary_scene,
                                                   interaction_name)

        current_interactions[self.co["output.options"]] = []
        current_interactions[self.co["output.dialouge"]] = []

        for option in interaction["options"]:
            condt = option["conditional"] if option["conditional"] != None else self.co["output.noconditional"]
            current_interactions[self.co["output.options"]].append([
                condt,
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
                rv[field["id"]]["scope_trees"].append(field["scope_tree"])
                rv[field["id"]]["line_nums"].append(field["line_num"])
                rv[field["id"]]["values"].append(field["value"])
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

    def i_parse_info_primary(self, field_name, field):
        if field_name == "version":
            v = utils.try_type(field["values"][-1], float)
            dbg = utils.dbg(self.logger, field["scope_trees"][-1]
                            ,field["scope_lines"][-1]
                            ,self.lines
                            ,field["file_name"])
            if not v[0]: # failed conversion
                dbg.error("syntax error", "parameter must be a version", field["line_nums"][-1])
            elif v[1] > VERSION:
                msg = "mads does not support version " + str(v[1])
                dbg.error("version error", msg, field["line_nums"][-1])
            elif v[1] < VERSION:
                self.logger.log("compiler", "version of file is less than mads version, some things may work incorrectly", 1)
        elif field_name == "support":
            for value, condition, line_num, scope_tree, scope_lines in zip(field["values"]
                                                                           ,field["conditionals"]
                                                                           ,field["line_nums"]
                                                                           ,field["scope_trees"]
                                                                           ,field["scope_lines"]):
                if value in self.options.support:
                    if condition == "false":
                        self.options.support[value] = False
                    else:
                        self.options.support[value] = True
                else:
                    dbg = utils.dbg(self.logger, scope_tree, scope_lines, self.lines, field["file_name"])
                    msg = "mads does not support " + value
                    dbg.error("support error", msg, line_num)
    
    # this function uses 'tag' as it is for both interactions
    # and scenes
    def i_check_required(self, tag_obj, required, tag_type):
        fields = [i["id"] for i in tag_obj["fields"]]
        for required_field in required:
            if required_field not in fields:
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
        # and compile info
        cnt = 0
        for i in self.tokens:
            for p in self.tokens[i]:
                cnt += 1
                if self.tokens[i][p]["type"] == "config":
                    config_scene = self.tokens[i][p]
                    self.logger.log("compiler", "compiling configuration", 3)
                    primary_fields = self.i_parse_info_fields(config_scene["fields"])
                    for field in primary_fields:
                        self.i_parse_info_primary(field, primary_fields[field])

                    for interaction in config_scene["interactions"]:
                        interaction_fields = self.i_parse_info_fields(config_scene["interactions"][interaction]["fields"])
                        # the tokenizer checks to make sure 
                        # it is a valid interaction
                        for field_name in interaction_fields:
                            field = interaction_fields[field_name]
                            dbg = utils.dbg(self.logger, field["scope_trees"][-1]
                                            ,field["scope_lines"][-1]
                                            ,self.lines
                                            ,field["file_name"])
                                            
                            match [interaction, *field["split"]]:
                                case ["declare.scene", "field", "require"]:
                                    self.scene_require.append(field["values"][-1])
                                case ["declare.interaction", "field", "require"]:
                                    self.interaction_require.append(field["values"][-1])
                                case [_, "field", "require"]:
                                    dbg.error("name error", "incorrect location for require", field["line_nums"][-1])
                                case ["declare.scene" | "declare.interaction", "field", "types", x]:
                                    self.scene_types_fields[x] = field["values"][-1]
                                case [_, "field", "types", _]:
                                    dbg.error("name error", "incorrect location for type definition", field["line_nums"][-1])
                                case ["compiler", *_]:
                                    if field_name in self.co:
                                        self.co[field_name] = field["values"][-1]
                                    else:
                                        error_msg = "compiler option does not exist" \
                                            + utils.did_you_mean(field_name, self.co)
                                        dbg.error("name error", error_msg, field["line_nums"][-1])
                                case [*_]:
                                    dbg.error("name error", "invalid option", field["line_nums"][-1])
        self.logger.bar_max = cnt

        for primary_scene in self.tokens:
            if primary_scene not in self.data:
                if primary_scene != "":
                    self.data[primary_scene] = { } # create the primary scene

            for secondary_scene in self.tokens[primary_scene]:
                self.logger.next("parsing scenes")
                scene = self.tokens[primary_scene][secondary_scene]

                if scene["type"] == "config": # if .info configuration
                    continue
                elif scene["type"] == "ref": # if reference
                    self.logger.log("compiler", "compiling reference " + scene["ref"], 3)
                    dbg = utils.dbg(self.logger
                                ,scene["scope_tree"]
                                ,scene["scope_lines"]
                                ,self.lines
                                ,scene["file_name"])
                    
                    print(scene)
                    if not self.options.support["scene-ref"]:
                        dbg.error("support error", "this mads script does not support scene-ref", scene["line_num"])
                    if scene["ref"] in self.scene_refs:
                        if self.options.support["full-ref"]:
                            self.data[primary_scene][secondary_scene] = scene["ref"]
                        else:
                            if scene["ref"].startswith(primary_scene):
                                scene_str = scene["ref"].replace(primary_scene + ".", "")
                                self.data[primary_scene][secondary_scene] = scene_str
                            else:
                                dbg.error("reference error", "reference must be part of current primary scene"
                                          , scene["line_num"])
                    else:
                        dbg.error("reference error", "scene '" + scene["ref"] + "' does not exist", scene["line_num"])
                else:
                    self.logger.log("compiler", "compiling tag " + primary_scene + "." + secondary_scene, 3)

                    entrypoint_list = []
                    # copy over the pre-defined entrypoints
                    for entrypoint in scene["entrypoints"]:
                        ref = self.i_parse_ref(primary_scene, secondary_scene,
                                                                    entrypoint["ref"],
                                                                    entrypoint["line_num"],
                                                                    entrypoint["scope_tree"],
                                                                    entrypoint["scope_lines"],
                                                                    entrypoint["file_name"])
                        
                        entrypoint_list.append([entrypoint["conditional"], ref])

                    default = {
                        self.co["output.interactions"]: {},
                        self.co["output.options"]: {},
                        self.co["output.dialouge"]: {},
                        self.co["output.entrypoints"]: entrypoint_list,
                    }

                    # create the secondary scene
                    self.data[primary_scene][secondary_scene] \
                            = self.i_parse_fields(scene["fields"], default, self.scene_types_fields,
                                                  primary_scene,
                                                  secondary_scene,
                                                  primary_scene + "." + secondary_scene)

                    for interaction_name in scene["interactions"]:
                        interaction_content = scene["interactions"][interaction_name]

                        self.data[primary_scene][secondary_scene][self.co["output.interactions"]][interaction_name] \
                            = self.i_parse_interaction(interaction_content, primary_scene, secondary_scene)
        
        self.logger.end()
        self.i_parse_required()