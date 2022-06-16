"""
    The python script for input verification and validation will perform the following task
        1. Check for the presence of the config file at given location.
        2. Check for the format of the config file at given location.
        3. Verify the variable name are in given format and not empty.
        4. Fetch the required data from the config file.
        5. Initialize the teamcity variable during runtime using teamcity service messages.
        6. Check for the presence of the input file required for this pipeline to run.
"""

import json
import os
import sys

build_number = sys.argv[1]
branch = sys.argv[2]

# Check if config file is present on given location
if os.path.exists("vecu_config.json"):
    print("config file present at "+os.getcwd()+"\\vecu_config.json")
else:
    sys.exit("config file not present at "+os.getcwd()+"\\vecu_config.json")

try:
    #open the config file
    json_ = open("vecu_config.json", "r")
    path_details = {}

    try:
        #check whether the json is in proper format
        path_details = json.load(json_)
    except Exception as e:
        sys.exit("Json format is incorrect")
    # variable name so that user does not enter wrong variable details
    data = ["sdp_file_path", "osa_file_path", "v_ecu_name", "container_file_path", "veos_build_tool", "output_file" ,
            "build_directory", "log_file_path ", "target", "xcp_service_port", "compiler_options", "cpp_compiler_options",
            "preprocessor_defines", "additional_code_files", "code_coverage_level", "show_all_warnings", "configuration",
            "osa_author", "upload_url", "zip_filename", "artifact_path","dap_arxml","module"]


    res = [ele for ele in data if (ele in path_details and (((ele == "preprocessor_defines" or ele == "additional_code_files")
        and isinstance(path_details[ele],list)) or (ele == "show_all_warnings" and isinstance(path_details[ele],bool)) or
        (ele != "preprocessor_defines" and ele != "additional_code_files" and ele != "show_all_warnings" and path_details[ele])))]

    # check if all the variable are present if yes proceed further or raise the error
    if len(res) == len(data):
        print("All variable are present in config file with respective data types")
    else:
        print(res)
        print(path_details)
        sys.exit("Please check the var name or data type of a particular variable entered in config file")
    
    #fetch the details from config file
    project_path = path_details.get("sdp_file_path")

    url = path_details.get("upload_url")
    zipfile_name = path_details.get("zip_filename")
    artifact_path = path_details.get("artifact_path")

    url = url + str(build_number)+"/"+str(zipfile_name)+".zip"

    # teamcity service message to set the variable values during runtime
    if branch == "development" or branch == "master" or branch == "refs/heads/development" or branch == "refs/heads/master":
        os.system("echo ##teamcity[setParameter name='deploy' value='true']")
        os.system("echo ##teamcity[setParameter name='vecu_artifacts_path' value='"+artifact_path+"']")
        os.system("echo ##teamcity[setParameter name='vecu_url' value='"+url+"']")
        os.system("echo ##teamcity[setParameter name='vecu_zipfile_name' value='"+zipfile_name+"']")
    else:
        os.system("echo ##teamcity[setParameter name='deploy' value='false']")

    #check if all input files are present at given location
    if(os.path.exists(project_path)):
        print("Input file present "+os.getcwd()+"\\"+project_path)
    else:
        sys.exit("Input file not present at "+os.getcwd()+"\\"+project_path)
except Exception as e:
    sys.exit("config file not found on location "+os.getcwd())
