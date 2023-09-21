import pickle
import json
import os

def dumpJson(data, file_name, options):
  json_data_string = ""
  if options.pretty:
    json_data_string = json.dumps(data, indent=4)
  else:
    json_data_string = json.dumps(data)

  with open(file_name, "w") as file:
    file.write(json_data_string)

def dumpPickle(data, file_name, options):
  pickle.dump(data, file_name)

def splitFileName(path_name):
  file_path, file_name = os.path.split(path_name)
  file_name_split = file_name.split(".")
  if len(file_name_split) >= 2:
    return os.path.join(file_path, ".".join(file_name_split[:-1])) + ".{value}." + file_name_split[-1]
  else:
    return path_name + "_{value}" # TODO: maybe format this a bit better

def getFileNames(data, file_name, options):
  if options.segment:
    file_names_content = []
    key_count = 0
    for primary_key in data:
      key_count += 1
      file_path = splitFileName(file_name)
      file_names_content.append(( file_path.format(value=str(key_count)), data[primary_key] ))
    return file_names_content
  else:
    return [(file_name, data)]

def dump(compiler_obj, file_name, options):
  file_content = getFileNames(compiler_obj.data, file_name, options)
  for file in file_content:
    if options.end_format == "json":
      dumpJson(file[1], os.path.join(options.cwd, file[0]), options)
    elif options.end_format == "pickle":
      dumpPickle(file[1], os.path.join(options.cwd, file[0]), options)