"""
    The python script for automation for building the .osa file will perform following operation
        1. Establish the connection with SystemDesk with headless mode.
        2. Get the Ecu name of the Active Project.
        3. Import new DAP configuration for the Active Project.
        4. Export the .vecu file for the Active Project.
        5. Build the .osa file for exported .vecu file fro the Active Project.
        6. Check if .osa file is generated in the given location.

"""
import Utilities
import os, json
import SystemDeskEnums
import time
import shutil
import logging
from win32com.client import Dispatch
import sys
import subprocess
import argparse

curr_dir = os.getcwd()
json_file = open("Scripts//config.json", "r")
path_details = json.load(json_file)
# Options
# This script uses the active project or the following file if no project is loaded in SystemDesk.
projectfile = path_details.get("sdp_file_path")
projectFile = curr_dir+'\\'+projectfile

# The name of the V-ECU to be build
vecuname = path_details.get("v_ecu_name")
vEcuName = vecuname

# The V-ECU is exported into this file
#containerFile = r'OpenSUT_Example.vecu'
cont_file = path_details.get("container_file_path")
containerFile = curr_dir+'\\'+cont_file

# Path to the VEOS build tool
veos_build_tool = path_details.get("veos_build_tool")
veosBuildTool = veos_build_tool

# The output file as string, specify this to create a simulation with more than one V-ECU
output_file = path_details.get("output_file")
outputFile = curr_dir+"\\"+output_file

# The directory that is used to store temporary files during build.
# Specify None to let VEOS chose the location.
build_directory = path_details.get("build_directory")
buildDirectory = curr_dir+"\\"+build_directory

# Path of the build logfile. If a relative path is specified the resulting path is determined relative to the buildDirectory.
log_file_path = path_details.get("log_file_path")
logFilePath = log_file_path

# The target board and compiler as string, possible values are 'HostPC32/GCC', 'HostPC32/MSVC', 'HostPC64/GCC', 'HostPC64/MSVC', 'HostPCLinux64/GCC'.
# Specify None to use the default build target of VEOS.
target_ = path_details.get("target")
target = target_

# The ethernet port to be used for calibration and measurement access.
# Specify None to use the default port of VEOS.
xcp_service_port = path_details.get("xcp_service_port")
xcpServicePort = None
if xcp_service_port != "None":
    xcpServicePort = xcp_service_port

# A string that is passed as argument to the C compiler. Specify None to omit this option.
compiler_options = path_details.get("compiler_options")
compilerOptions = None
if compiler_options != "None":
    compilerOptions = compiler_options

# A string that is passed as argument to the C++ compiler. Specify None to omit this option.
cpp_compiler_options = path_details.get("cpp_compiler_options")
cppCompilerOptions = None
if cpp_compiler_options != "None":
    cppCompilerOptions = cpp_compiler_options

# A list used to specify preprocessor defines.
preprocessor_defines = path_details.get("preprocessor_defines")
preprocessorDefines = preprocessor_defines
#preprocessorDefines = ['OPENSUT_DEBUG_ON'  ]

# A list of files to be included in the V-ECU.
additional_code_files = path_details.get("additional_code_files")
additionalCodeFiles = additional_code_files

# The code coverage level, possible values are 'None', 'FunctionCoverage', 'DecisionCoverage', 'MultiConditionCoverage', 'TimingExclusive', 'TimingInclusive'
code_coverage_level = path_details.get("code_coverage_level")
codeCoverageLevel = None
if code_coverage_level != "None":
    codeCoverageLevel = code_coverage_level

# A flag used to configure the compiler to output all warnings.
#show_all_warnings = path_details.get("show_all_warnings")
showAllWarnings = False
#if not show_all_warnings:
    #showAllWarnings = show_all_warnings

# The build configuration, possible values are 'Debug' and 'Release'. Specify None to use the default value of VEOS, i.e. 'Debug'.
configuration_ = path_details.get("configuration")
configuration = configuration_

# A string used to specify the author of the output file.
osa_author = path_details.get("osa_author")
osaAuthor = None
if osa_author != "None":
    osaAuthor = osa_author

dap_arxml = path_details.get("dap_arxml")
module = path_details.get("module")

# Constants
(scriptName, ext) = os.path.splitext(os.path.basename(__file__))


# Function to start the systemDesk application in headless mode.
def getSystemDesk():
    """Open COM connection to SystemDesk"""
    try:
        sd = Dispatch("SystemDesk.Application")
        sd.Visible = False #to disable the ui
        sd.BatchMode = True
    except Exception as e:
        sys.exit("Unable to connect to SystemDesk please check the license or close the running instance")
    if (sd == None):
        raise Exception("Could not find SystemDesk.")
    return sd

# Function to get the vecu name from given sdp Project.
def getVEcu(sd):
    """Get V-ECU to be built"""
    if (sd.ActiveProject == None):
        if not os.path.exists(projectFile):
            raise Exception("Cannot find the project file at " + projectFile + ".")

        sd.OpenProject(projectFile)
        if (sd.ActiveProject == None):
            msg = 'Failed to open the required project: %s' % projectFile
            sd.SubmitErrorMessage(scriptName, msg)
            raise Exception(msg)
    vEcu = sd.ActiveProject.VEcus.Item(vEcuName)
    if (vEcu == None) or (vEcu.ElementType != 'IClassicVEcu' and vEcu.ElementType != 'IAdaptiveVEcu'):
        msg = 'Failed to get the required V-ECU: %s' % vEcuName
        sd.SubmitErrorMessage(scriptName, msg)
        raise Exception(msg)
    return vEcu

#Function to modify the DAP config with new DAP arxml file
def dap_config(sd,vecu):
    print("Removing DAP Module")
    vecu_imp = vecu.VEcuImplementation
    packages=vecu_imp.Packages.Elements
    vecu_imp.Packages.Remove(packages[-1])
    print("DAP Module removed")
    
    print("Importing new Dap Module")
    try:
        import_arxml = vecu_imp.ImportModuleConfiguration(dap_arxml,module)
    except Exception as e:
        sys.exit("Failed to import module configuration check the path entered")
    print("DAP Module imported")

#Function to export the vecu container at given location
def exportContainer(sd, vEcu):
    """Export V-ECU implementation"""
    try:
        container = vEcu.ExportContainer(os.path.abspath(containerFile))
    except Exception as e:
        sys.exit("Failed to export the .vecu container check the logs")
    if (container == None):
        msg = 'V-ECU implementation export failed.'
        sd.SubmitErrorMessage(scriptName, msg)
        raise Exception(msg)
    print("V-ECU implementation successfully exported: %s" % container)
    return container

#Function used to build the .osa file using the VEOS executable 
def callVeosBuild(sd, vEcu, container):
    """Build V-ECU with VEOS Player"""
    print("Starting build of the V-ECU implementation", vEcu.Name)

    if not os.path.exists(veosBuildTool):
        print("Cannot find the VEOS build tool at " + veosBuildTool + ", install VEOS 5.1 or newer.")
        return None

    buildAction = 'classic-vecu'
    if vEcu.ElementType == 'IAdaptiveVEcu':
        buildAction = 'adaptive-vecu'

    arguments = str.format('"{}" {} "{}"', veosBuildTool, buildAction, container)
    if outputFile != None:
        arguments += ' -o "' + outputFile + '"'
        sd.SubmitInfoMessageWithUrl('BuildScript', "Writing simulation system to", outputFile)
    if buildDirectory != None:
        arguments += ' --build-directory "' + buildDirectory + '"'
    if logFilePath != None:
        if os.path.isabs(logFilePath):
            absoluteLogFilePath = logFilePath
        else:
            absoluteLogFilePath = os.path.normpath(os.path.join(buildDirectory, logFilePath))
        arguments += ' --log-file-path "' + absoluteLogFilePath + '"'
        sd.SubmitInfoMessageWithUrl('BuildScript', "Writing build logfile to", absoluteLogFilePath)
    if target != None:
        arguments += ' -t ' + target
    if xcpServicePort != None:
        arguments += ' --xcp-service-port {0}'.format(xcpServicePort)
    if compilerOptions != None:
        arguments += ' --compiler-options="' + compilerOptions + '"'
    if cppCompilerOptions != None:
        arguments += ' --cpp-compiler-options="' + cppCompilerOptions + '"'
    if len(preprocessorDefines) > 0:
        arguments += ' --preprocessor-defines="' + ' '.join(preprocessorDefines) + '"'
    if len(additionalCodeFiles) > 0:
        arguments += ' --additional-code-files "' + '" "'.join(additionalCodeFiles) + '"'
    if codeCoverageLevel != None:
        arguments += ' --code-coverage-level ' + codeCoverageLevel
    """if showAllWarnings:
        arguments += ' --show-all-warnings'"""
    if configuration != None:
        arguments += ' --configuration ' + configuration
    if osaAuthor:
        arguments += ' --osa-author "' + osaAuthor + '"'

    print(arguments)
    return subprocess.run(arguments)

#initiation of the build
def build():
    """Mаin function"""
    startMsg = 'Starting execution of build script: %s' % __file__
    print(startMsg)
    sd = getSystemDesk()
    sd.SubmitInfoMessage(scriptName, startMsg)
    vEcu = getVEcu(sd)
    dap_config(sd,vEcu)
    container = exportContainer(sd, vEcu)
    buildResult = callVeosBuild(sd, vEcu, container)

    returncode = 0
    if buildResult != None:
        returncode = buildResult.returncode
    else:
        returncode = -1

    if returncode == 0:
        sd.SubmitInfoMessage('BuildScript', "VEOS Build finished successfully.")
    else:
        sd.SubmitErrorMessage('BuildScript', "VEOS Build finished with errors. See the Build log for details.")

    time.sleep(10)
    sd.Quit()
    time.sleep(5)
    if os.path.exists(outputFile):
        print(".osa file generated succesfully at locationn "+outputFile)
    else:
        sys.exit(".osa file is not generated at location "+outputFile)
    return returncode

#Function that is used to add the new defines
def setOrReplaceDefine(define):
    name = define.split('=', 1)[0]
    for i in range(len(preprocessorDefines)):
        if preprocessorDefines[i] == name or preprocessorDefines[i].startswith(name + '='):
            preprocessorDefines[i] = define
            break
    else:
        preprocessorDefines.append(define)

# Entry point 
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start build of V-ECU ' + vEcuName, allow_abbrev=False)
    parser.add_argument('-o', '--outputFile', help='Name of the OSA file.')
    parser.add_argument('--buildDirectory', help='The directory that shall be used to store build artefacts.')
    parser.add_argument('--logFilePath', help='Path of the build logfile.')
    parser.add_argument('--compilerOptions', help='Additional C compiler options.')
    parser.add_argument('--cppCompilerOptions', help='Additional C++ compiler options.')
    parser.add_argument('--preprocessorDefines', nargs='+', help='Preprocessor defines.')
    parser.add_argument('--additionalCodeFiles', nargs='+', help='Additional code files.')
    parser.add_argument('--showAllWarnings', action='store_true', default=None, help='Show all compiler warnings.')
    parser.add_argument('--configuration', choices=['Debug', 'Release'], help='Specifies the build configuration.')
    parser.add_argument('--osaAuthor', help='Name of the OSA file author')

    args = parser.parse_args()

    if args.outputFile != None:
        outputFile = os.path.abspath(args.outputFile)

    if args.buildDirectory != None:
        buildDirectory = os.path.abspath(args.buildDirectory)

    if args.logFilePath != None:
        logFilePath = args.logFilePath

    if args.compilerOptions != None:
        compilerOptions += ' ' + args.compilerOptions.strip("'")

    if args.cppCompilerOptions != None:
        cppCompilerOptions += ' ' + args.cppCompilerOptions.strip("'")

    if args.preprocessorDefines != None:
        for define in args.preprocessorDefines:
            setOrReplaceDefine(define)

    if args.additionalCodeFiles != None:
        additionalCodeFiles.extend(args.additionalCodeFiles)
        
    if args.showAllWarnings != None:
        showAllWarnings = args.showAllWarnings

    if args.configuration != None:
        configuration = args.configuration

    if args.osaAuthor != None:
        osaAuthor = args.osaAuthor

    sys.exit(build())
