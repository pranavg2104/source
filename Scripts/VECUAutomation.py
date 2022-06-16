import importlib
import sys
import os
import time
import win32com.client


#------------------------------------------------------------------------------
class OptionsHelper():  # pylint: disable=too-few-public-methods
    """
    This class defines some options which are used for configuration of the project.
    """
    def __init__(self):
        # Name of the project.
        self.ProjectName = "Untitled"


#===============================================================================
# Global variables for easier access to elements in SystemDesk.
#===============================================================================

# Global variable containing configuration options.
Options = OptionsHelper()

# The SystemDesk application object. This object is None until
# ConnectToSystemDesk() is successfully performed.
SdApplication = None

# SystemDesk automation enum definitions. This object is None until
# ConnectToSystemDesk() is successfully performed.
SdEnums = None

# The VEOS Player application object. This object is None until
# ConnectToVeosPlayer() is successfully performed.
VpApplication = None

# VeosPlayer automation enum definitions. This object is None until
# ConnectToVeosPlayer() is successfully performed.
VpEnums = None


#===============================================================================
# Utility methods.
#===============================================================================

def BuildModelContainerForVeos(vpProject, containerPath="", buildPath=None, xcpPort=None):
    """
    Import a Model Implementation Container (VECU, SIC, BSC, FMU) and build it for VEOS.
    Note, that the OSA file is saved and reopened during the build process.
    Therefore existing COM objects for VEOS Player project elements become invalid.
    """

    # Check preconditions.
    if (containerPath in (None, "")):
        raise Exception("Path of model implementation container is not specified")
    if not os.path.exists(containerPath):
        raise Exception("Model implementation container does not exist at path: %s" % containerPath)
    containerFileName = os.path.basename(containerPath)
    (vpuName, fileExt) = os.path.splitext(containerFileName)
    if not (".vecu", ".sic", ".bsc", ".fmu").__contains__(fileExt.lower()):
        buildStatus = VpEnums.BuildStatusEnum.Invalid
        raise Exception("Name of container file %s does not end with valid extension (.vecu, .sic, .bsc, .fmu)" % containerFileName)
    osaFile = vpProject.SystemFile
    ##if vpProject.Vpus.Item(vpuName):
    if vpProject.Vpus.Names.__contains__(vpuName):
        vpProject.RemoveVpu(vpuName)
        vpProject.Save(osaFile)

    # Configure the importer.
    importSettings = vpProject.CreateNewImportSettings()
    importSettings.ImportFilePath = containerPath
    if xcpPort:
        importSettings.XcpPort = xcpPort
    if buildPath:
        importSettings.BuildDirectoryPath = buildPath
    importSettings.EnableDebugBuild = False
    importSettings.EnableDebugBuild = True

    buildResult = None
    try:
        # Run the importer and build VPU.

        buildResult = vpProject.Import(importSettings)
        buildStatus = buildResult.BuildStatus

        if Isa(buildStatus, "int"):
            buildStatus = VpEnums.BuildStatusEnum(buildStatus)
    except Exception:
        buildStatus = VpEnums.BuildStatusEnum.Invalid

    # Check the build status.
    if buildStatus == VpEnums.BuildStatusEnum.Valid:
        print("Build of %s finished with status VALID" % vpuName)
    else:
        # Print build output and throw exception.
        if buildResult != None:
            print("Output of build: \n\n " + buildResult.BuildOutput)
        print("*** Build finished with status " + str(buildStatus))
        raise Exception("Build of %s aborted with status %s" % (containerFileName, buildStatus))

    return buildStatus

def ConnectToVeosPlayer():
    """
    Opens a COM connection to the VEOS Player.
    """
    global VpApplication
    global VpEnums
    if VpApplication == None:
        print("Opening COM connection to VEOS Player")
        # try to connect to VEOS Player 5.1 or 5.2
        try:
            VpApplication = win32com.client.Dispatch("VeosPlayer.Application.5.1")
        except Exception:
            pass
        if not VpApplication:
            VpApplication = win32com.client.Dispatch("VeosPlayer.Application.5.2")
        if not VpApplication:
            raise Exception("Could not dispatch VEOS Player 5.1 or 5.2")

        # Append VeosPlayers's scripting directory to the Python search path.
        applicationRootDir = VpApplication.ApplicationRootDir
        if os.path.basename(applicationRootDir).lower() == "bin":   ## HACK!! removes .\bin at the end of the path
            applicationRootDir = os.path.dirname(VpApplication.ApplicationRootDir)
        scriptingDir = os.path.join(applicationRootDir + r"\Tools\Scripting")
        if not sys.path.__contains__(scriptingDir):
            sys.path.insert(0, scriptingDir)
        # The enum definitions are needed later.
        import VeosEnums
        importlib.reload(VeosEnums)
        VpEnums = VeosEnums
    return VpApplication


def GetVeosProject(osaFile):
    """
    Returns a VEOS Player project for the given OSA file.
    The active project is reused if the OSA file is already open. Otherwise a new project is created.
    """
    # Get the VEOS Player project.
    vpProject = VpApplication.Projects.Active
    if not vpProject:
        if os.path.exists(osaFile):
            # Open the OSA file with VEOS Player.
            vpProject = VpApplication.Projects.Open(osaFile)
        else:
            # Create new OSA file.
            vpProject = VpApplication.Projects.CreateNew(osaFile)
        if (not vpProject):
            raise Exception("OSA file '%s' could not be opened." % osaFile)
    else:
        if vpProject.SystemFile != osaFile:
            raise Exception("Another OSA file is opened in VEOS Player: '%s'. Close this file first." % vpProject.SystemFile)

    return vpProject

def DisconnectFromVeosPlayer():
    """
    Closes a COM connection to the VEOS Player and disposes the vpApplication object.
    """
    global VpApplication
    if VpApplication != None:
        VpApplication.Quit()
        VpApplication = None

def Isa(obj, typeName):
    """
    Returns True if the 'obj' is of type 'typeName'.
    """
    if str(obj.__class__).__contains__("'" + typeName + "'"):
        return True
    else:
        return False


def IsBoolean(obj):
    """
    Returns True if the 'obj' is of boolean type.
    """
    if str(obj.__class__).__contains__("'bool'"):
        return True
    elif str(obj.__class__).__contains__("'bool'") and bool(obj):
        return IsBoolean(obj[0])
    elif str(obj.__class__).__contains__("'tuple'") and bool(obj):
        return IsBoolean(obj[0])
    else:
        return False


def IsNumerical(obj):
    """
    Returns True if the 'obj' is of numerical type (i.e. 'float', 'int').
    """
    if str(obj.__class__).__contains__("'float'"):
        return True
    elif str(obj.__class__).__contains__("'int'"):
        return True
    elif str(obj.__class__).__contains__("'list'") and bool(obj):
        return IsNumerical(obj[0])
    elif str(obj.__class__).__contains__("'tuple'") and bool(obj):
        return IsNumerical(obj[0])
    else:
        return False


def Value2Str(value):
    """
    Formats a numerical or boolean value as a string.
    """
    if IsBoolean(value):
        if value:
            return "1"
        else:
            return "0"
    elif value == int(value):
        return str(int(value))
    else:
        return str(value)


def TrimEnd(str1, str2):
    """
    Removes str2 from the end of str1.
    """
    if str1.endswith(str2):
        return str1[0:len(str1)-len(str2)]
    else:
        return str1


def ToPascal(str1):
    """
    Converts a string to Pascal style, i.e. first letter in upper case
    and following characters in lower case.
    E.g. "CAN" -> "Can"
    """
    return str1[0:1].upper() + str1[1:len(str1)].lower()


#------------
# Assertions.
#------------

def ThrowIfError(messages, command="Command"):
    """
    Checks if a message list returned by a SystemDesk command contains any errors.
    If yes, the first error message is displayed and an exception is thrown.
    """
    if not messages:
        print("Command '%s' does not return a message object." % command)
        return
    errorMessages = messages.ErrorMessages
    if errorMessages.Count == 0:
        return
    # An error has occured.
    firstError = errorMessages.Elements[0]
    if errorMessages.Count == 1:
        msg = "%s aborted with %s:\n%s\nSee Message Browser." % \
            (command, firstError.MessageIdentifier, firstError.MessageText, )
    else:
        msg = "%s aborted with errors. First message was %s:\n%s\nSee Message Browser." % \
            (command, firstError.MessageIdentifier, firstError.MessageText, )
    # Throw exception.
    raise Exception(msg)

def AssertIf(condition, message):
    """
    Throws an assertion if the condition is True.
    """
    if condition:
        assert 0, message


#-------------------------
# Debugging and profiling.
#-------------------------

def PrintD(message):
    """
    Prints a message if debugging is enabled.
    """
    if os.path.exists("__ENABLE_DEBUG__"):
        print("*** DEBUG: %s" % message)


class _MiniProfiler():
    """
    This class defines some options which can be used to configure the
    structure of a project.
    """
    def __init__(self):
        self._StartTime = 0.0
        self._LastTime = 0.0
        self._CurrentTime = 0.0
        self.Start()

    def Start(self):
        """
        Starts the time measurement.
        """
        self._StartTime = time.clock()
        self._LastTime = self._StartTime
        self._CurrentTime = self._StartTime

    def DeltaTime(self, display=True):
        """
        Returns the time since the last call of DeltaTime() or __init__().
        """
        self._CurrentTime = time.clock()
        deltaTime = self._CurrentTime - self._LastTime
        self._LastTime = self._CurrentTime
        if display:
            PrintD("DeltaTime =%6.3f sec" % deltaTime)
        return deltaTime

    def TotalTime(self, display=True):
        """
        Returns the time since the last call of Start() or __init__().
        """
        self._CurrentTime = time.clock()
        totalTime = self._CurrentTime - self._StartTime
        if display:
            PrintD("TotalTime =%6.3f sec" % totalTime)
        return totalTime

# Create a global instance of the MiniProfiler.
MiniProfiler = _MiniProfiler()




