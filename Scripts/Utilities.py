"""
--------------------------------------------------------------------------------
File:        Utilities.py

Description: Provides some utility classes and methods which are frequently
             used in SystemDesk demos.

Tip/Remarks: -

Limitations: -

Version:     5.5

Since:       2007-01-16

             dSPACE GmbH shall not be liable for errors contained herein or
             direct, indirect, special, incidental, or consequential damages
             in connection with the furnishing, performance, or use of this
             file.
             Brand names or product names are trademarks or registered
             trademarks of their respective companies or organizations.

Copyright (c) 2020 by dSPACE GmbH, Paderborn, Germany
  All Rights Reserved.
--------------------------------------------------------------------------------
"""

import importlib
import sys
import os
import time
import win32com.client
import shutil

#path = 'D:\Cicd_Implementation\Virtual_ECU\SystemDeskProject\Production_Asw_Rte_Sim'
#------------------------------------------------------------------------------
path = 'D:\ASW+BSW\VECU_Build\Automation\Project'

class OptionsHelper():
    """
    This class defines some options which are used for configuration of the project.
    """
    def __init__(self):
        self._ProjectName = "Untitled"

    @property
    def ProjectName(self):
        """
        Gets the name of the project.
        """
        return self._ProjectName
    @ProjectName.setter
    def ProjectName(self, value):
        """
        Sets the name of the project.
        """
        self._ProjectName = value


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

def AddBusConnectorAndPorts(ecuInstance, commController, busConnectorName=None):
    """
    Creates a new
        communication connector,
        frame in/out ports,
        IPdu in/out ports,
        ISignal in/out ports,
    for a bus.
    """

    # Create bus connector.
    if commController.ElementType == "ICanCommunicationController":
        busType = "Can"
        commConnector = ecuInstance.Connectors.AddNewCanCommunicationConnector()
    elif (commController.ElementType == "ILinMaster") or (commController.ElementType == "ILinSlave"):
        busType = "Lin"
        commConnector = ecuInstance.Connectors.AddNewLinCommunicationConnector()
    else:
        raise Exception("AddBusConnectorAndPorts() not implemented for bus type " + busType)
    if not busConnectorName:
        # Remove trailing "CommController" or "CommunicationController" to determine the bus name.
        busName = TrimEnd(commController.ShortName, "Controller")
        busName = TrimEnd(busName, "Communication")
        busName = TrimEnd(busName, "Comm")
        busConnectorName = ecuInstance.ShortName + busName + "Connector"
    commConnector.ShortName = busConnectorName
    commConnector.CommControllerRef = commController

    # FramePorts
    portNamePrefix = TrimEnd(busConnectorName, "Connector")
    framePortOut = commConnector.EcuCommPortInstances.AddNewFramePort(portNamePrefix + "FramePortOut")
    framePortOut.CommunicationDirection = SdEnums.CommunicationDirectionTypeEnum.Out
    framePortIn = commConnector.EcuCommPortInstances.AddNewFramePort(portNamePrefix + "FramePortIn")
    framePortIn.CommunicationDirection = SdEnums.CommunicationDirectionTypeEnum.In
    # IPduPorts
    iPduPortOut = commConnector.EcuCommPortInstances.AddNewIPduPort(portNamePrefix + "IPduPortOut")
    iPduPortOut.CommunicationDirection = SdEnums.CommunicationDirectionTypeEnum.Out
    iPduPortIn = commConnector.EcuCommPortInstances.AddNewIPduPort(portNamePrefix + "IPduPortIn")
    iPduPortIn.CommunicationDirection = SdEnums.CommunicationDirectionTypeEnum.In
    # ISignalPorts
    iSignalPortOut = commConnector.EcuCommPortInstances.AddNewISignalPort(portNamePrefix + "ISignalPortOut")
    iSignalPortOut.CommunicationDirection = SdEnums.CommunicationDirectionTypeEnum.Out
    iSignalPortIn = commConnector.EcuCommPortInstances.AddNewISignalPort(portNamePrefix + "ISignalPortIn")
    iSignalPortIn.CommunicationDirection = SdEnums.CommunicationDirectionTypeEnum.In

    return commConnector


def AddDisabledMode(rteEvent, modePort, modeDeclaration):
    """
    Creates a new mode disabling dependency for the given mode.
    The modeDeclarationGroupPrototype is determined by the ModeSwitchInterface
    at the given port.
    The parameter modeDeclaration may either be a ModeDeclaration or it's
    ShortName.
    """
    mdgPrototype = modePort.RequiredInterfaceTref.ModeGroup
    if Isa(modeDeclaration, "str"):
        modeDeclaration = mdgPrototype.TypeTref.ModeDeclarations.Item(modeDeclaration)
    rModeInAtomicSwcIref = rteEvent.DisabledModeIrefs.AddNew()
    rModeInAtomicSwcIref.ContextPortRef = modePort
    rModeInAtomicSwcIref.ContextModeDeclarationGroupPrototypeRef = mdgPrototype
    rModeInAtomicSwcIref.TargetModeDeclarationRef = modeDeclaration


def AddFibexElement(system, fibexElement):
    """
    Adds a fibex element to the given system.
    """
    fibexElementConditional = system.FibexElements.AddNew()
    fibexElementConditional.FibexElementRef = fibexElement


def AddLinScheduleTableEntry(scheduleTable, delay, frameTriggering):
    """
    Creates a new application entry in a LIN schedule table.
    """
    tableEntry = scheduleTable.TableEntrys.AddNewApplicationEntry()
    tableEntry.Delay = delay
    tableEntry.PositionInTable = scheduleTable.TableEntrys.Count - 1
    tableEntry.IsPositionInTableDefined = True
    tableEntry.FrameTriggeringRef = frameTriggering


def AddModeAccessPointModeIref(modeAccessPoint, modePort, modeDeclaration):
    """
    Creates a new mode instance reference for the given mode.
    The modeDeclarationGroupPrototype is determined by the ModeSwitchInterface
    at the given port. The parameter modeDeclaration may either be a
    ModeDeclaration or it's ShortName.
    """
    mdgPrototype = modePort.RequiredInterfaceTref.ModeGroup
    if Isa(modeDeclaration, "str"):
        modeDeclaration = mdgPrototype.TypeTref.ModeDeclarations.Item(modeDeclaration)
    rModeGroupInAtomicSwcIref = modeAccessPoint.SetNewModeGroupIrefRModeGroupInAtomicSWCInstanceRef()
    rModeGroupInAtomicSwcIref.ContextRPortRef = modePort
    rModeGroupInAtomicSwcIref.TargetModeGroupRef = mdgPrototype
    mapIdent = modeAccessPoint.SetNewIdent()
    mapIdent.ShortName = modeAccessPoint.GetGeneratedName()


def AddModeSwitchPointModeIref(modeSwitchPoint, modePort, modeDeclaration):
    """
    Creates a new mode instance reference for the given mode.
    The modeDeclarationGroupPrototype is determined by the ModeSwitchInterface
    at the given port. The parameter modeDeclaration may either be a
    ModeDeclaration or it's ShortName.
    """
    mdgPrototype = modePort.RequiredInterfaceTref.ModeGroup
    if Isa(modeDeclaration, "str"):
        modeDeclaration = mdgPrototype.TypeTref.ModeDeclarations.Item(modeDeclaration)
    rModeInAtomicSwcIref = modeSwitchPoint.ModeIrefs.AddNew()
    rModeInAtomicSwcIref.ContextPortRef = modePort
    rModeInAtomicSwcIref.ContextModeDeclarationGroupPrototypeRef = mdgPrototype
    rModeInAtomicSwcIref.TargetModeDeclarationRef = modeDeclaration


def AddModuleConfiguration(ecuConfiguration, bswModuleName, importToProject=False, moduleName=None):
    """
    Creates a new module configuration for the given basic software module
    (e.g. "Os") and adds it to the EcuConfiguration.
    """
    global SdApplication

    if moduleName == None:
        moduleName = bswModuleName

    # Name of the file containing EcucModuleDefs for supported BSW modules.
    moduleDefinitionFile = SdApplication.EcuConfigurationManager.DefaultDefinitionFilename

    # Determine the package containing the BSW module definition.
    if ("Rte", "MemMap", "Platform",).__contains__(bswModuleName):
        definitionPackage = "/dSPACE"
    elif ("DsIdBusIf",).__contains__(bswModuleName):
        definitionPackage = "/dSPACE_VEOS"
    else:
        definitionPackage = "/dSPACE_Sim"

    # Check if a module definition already exists.
    moduleDefinitionArPath = definitionPackage + "/" + bswModuleName
    moduleDefinition = GetElementByPath(moduleDefinitionArPath)
    if False and moduleDefinition:
        # Create a new module configuration using the existing module definition.
        moduleConfiguration = SdApplication.EcuConfigurationManager.AddModuleConfigurationByDef( \
            ecuConfiguration, \
            moduleDefinition, \
            moduleName)
        moduleConfiguration.DefinitionFilename.Value = moduleDefinitionFile
    else:
        # Create a new module configuration by importing the module definition from file.
        moduleConfiguration = SdApplication.EcuConfigurationManager.AddModuleConfigurationByFile( \
            ecuConfiguration, \
            moduleDefinitionArPath, \
            moduleDefinitionFile, \
            importToProject, \
            moduleName)
    assert moduleConfiguration, "Could not find module definition " + moduleDefinitionArPath

    return moduleConfiguration


def AddRteEventMapping(ecuConfiguration, osTask, componentName, rteEventName, \
    osEvent=None, osAlarm=None, positionInTask=None):
    """
    Adds a RunnableEntityMapping for the given RTE event to the RTE configuration.
    """
    rteConfiguration = FindModuleConfiguration(ecuConfiguration, "Rte")

    # Get the component prototype and the RTE event.
    ecuFlatView = ecuConfiguration.EcuExtractSystem.RootSwCompositionPrototype
    rootSwComposition = ecuFlatView.SoftwareCompositionTref
    component = rootSwComposition.Components.Item(componentName)
    rteEvent = component.TypeTRef.InternalBehaviors.Elements[0].Events.Item(rteEventName)

    # Determine the next free PositionInTask.
    if not positionInTask:
        positionInTask = FindNextPositionInTask(rteConfiguration, osTask)

    # Find the SwComponentInstance in the RTE configuration.
    swcInstance = rteConfiguration.RteSwComponentInstances.Item(componentName)

    # Create a new runnable entity mapping.
    runnableEntityMapping = swcInstance.RteEventToTaskMappings.Add(rteEventName)
    runnableEntityMapping.RteMappedToTaskRef = osTask
    runnableEntityMapping.RteEventRef = rteEvent
    runnableEntityMapping.RtePositionInTask = positionInTask
    if osEvent:
        runnableEntityMapping.RteUsedOsEventRef = osEvent
    if osAlarm:
        runnableEntityMapping.RteUsedOsAlarmRef = osAlarm


def AddISignalToPduMapping(iPdu, iSignalOrISignalGroup, startPosition=0, \
    packingByteOrder=None, transferProperty=None):
    """
    Adds an ISignalToPduMapping to an IPdu for the given ISignal or ISignalGroup.
    """
    if packingByteOrder == None:
        packingByteOrder = SdEnums.ByteOrderEnum.MostSignificantByteLast ## LittleEndian
    if transferProperty == None:
        transferProperty = SdEnums.TransferPropertyEnum.Pending ## send in ComMainFunction

    iSignalToPduMapping = iPdu.ISignalToPduMappings.AddNew(iSignalOrISignalGroup.ShortName)
    if iSignalOrISignalGroup.ElementType == "IISignal":
        iSignalToPduMapping.ISignalRef = iSignalOrISignalGroup
    elif iSignalOrISignalGroup.ElementType == "IISignalGroup":
        iSignalToPduMapping.ISignalGroupRef = iSignalOrISignalGroup
    else:
        raise Exception("Invalid type of parameter iSignalOrISignalGroup: " + iSignalOrISignalGroup.ElementType)
    iSignalToPduMapping.StartPosition = startPosition
    iSignalToPduMapping.PackingByteOrder = packingByteOrder
    iSignalToPduMapping.TransferProperty = transferProperty
    return iSignalToPduMapping


def ApplySwBaseType(arElement, swBaseType):
    """
    Applies an existing SwBaseType to an AUTOSAR element.
    """
    GetOrCreateSwDataDefProps(arElement).TrySetBaseTypeRef(swBaseType)

def ApplyCompuMethod(arElement, compuMethod):
    """
    Applies an existing CompuMethod to an AUTOSAR element.
    """
    GetOrCreateSwDataDefProps(arElement).TrySetCompuMethodRef(compuMethod)


def ApplyDataConstr(arElement, dataConstr):
    """
    Applies an existing DataConstr to an AUTOSAR element.
    """
    GetOrCreateSwDataDefProps(arElement).TrySetDataConstrRef(dataConstr)


def ApplyDisplayFormat(arElement, displayFormat):
    """
    Applies the given DisplayFormat to an AUTOSAR element.
    """
    arElement.GetOrCreateSwDataDefProps().DisplayFormat = displayFormat


def ApplyUnit(arElement, unit):
    """
    Applies an existing Unit to an AUTOSAR element.
    """
    arElement.GetOrCreateSwDataDefProps().TrySetUnitRef(unit)


def AssignMemMapAddressingModeSet(memMapConfiguration, sectionName, addressingModeSet):
    """
    Assigns the given addressingModeSet to the given section for all existing
    MemMapAllocations.
    """
    # First priority: Check if the sectionName matches MemorySection.Symbol
    for memMapAllocation in memMapConfiguration.MemMapAllocations.Elements:
        for sectionMapping in memMapAllocation.MemMapSectionSpecificMappings.Elements:
            if not sectionMapping.MemMapAddressingModeSetRef:
                memorySection = sectionMapping.MemMapMemorySectionRef
                memorySectionSymbol = memorySection.Symbol
                if (memorySectionSymbol in (sectionName, sectionName + "BIT")):
                    sectionMapping.MemMapAddressingModeSetRef = addressingModeSet

    # Second priority: Check if the sectionName matches MemorySection.ShortName
    for memMapAllocation in memMapConfiguration.MemMapAllocations.Elements:
        for sectionMapping in memMapAllocation.MemMapSectionSpecificMappings.Elements:
            if not sectionMapping.MemMapAddressingModeSetRef:
                memorySection = sectionMapping.MemMapMemorySectionRef
                memorySectionName = memorySection.ShortName
                if (memorySectionName in (sectionName, sectionName + "BIT")):
                    sectionMapping.MemMapAddressingModeSetRef = addressingModeSet


def BuildForVeos(simSystem, vEcuName=None):
    """
    Build an Offline Simulation Application (OSA) for VEOS.
    If no V-ECU name is specified, then the whole simulation system is build.
    """
    global SdApplication
    if vEcuName != None:
        vEcu = simSystem.ClassicVEcus.Item(vEcuName)
        assert vEcu != None, "V-ECU %s does not exist" % vEcuName
    else:
        vEcu = None

    # Run the build. Catch exceptions.
    oldBatchMode = SdApplication.BatchMode
    SdApplication.BatchMode = True
    try:
        if vEcu == None:
            # Build whole simulation system.
            buildResult = simSystem.Build()
            buildStatus = buildResult.BuildStatus
        else:
            # Build single V-ECU.
            buildResult = vEcu.Build()
            buildStatus = buildResult.BuildStatus
        if Isa(buildStatus, "int"):
            buildStatus = SdEnums.BuildStatusEnum(buildStatus)
    except Exception:
        buildStatus = SdEnums.BuildStatusEnum.Invalid
    finally:
        SdApplication.BatchMode = oldBatchMode

    return buildStatus

def BuildForVeosUsingVeosPlayer(osaDir, vEcuPath, vEcuName, xcpServicePort, forceGcc=False):
    """
    Build an Offline Simulation Application (OSA) for VEOS.
    If no V-ECU name is specified, then the whole simulation system is build.
    """

    # Open COM connection to VEOS Player.
    try:
        vpApplication = ConnectToVeosPlayer()
    except Exception:
        print("VEOS Player could not be dispatched.")
        return VpEnums.BuildStatusEnum.Invalid

    buildDir = os.path.join(osaDir, vEcuName)
    # Build the V-ECU.
    buildStatus = BuildModelContainerForVeos(vpApplication.Projects.Active, \
        containerPath=vEcuPath, \
        buildPath=buildDir, \
        xcpPort=xcpServicePort, \
        gcc=forceGcc)

    return buildStatus

def CopyBuildLog(osaFile, vecuName):
    """
    Copies the general build log file to a V-ECU specific location and file name.
    """
    path = os.path.splitext(osaFile)[0]
    logFile = path + ".Build.log"
    path = os.path.dirname(path)
    shutil.copyfile(logFile, os.path.join(os.path.join(path, vecuName), "Build.log"))


def BuildModelContainerForVeos(vpProject, containerPath="", buildPath=None, xcpPort=None, debug=True, gcc=False):
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
        raise Exception("Name of container file %s does not end with valid extension (.vecu, .sic, .bsc, .fmu)" % containerFileName)
    osaFile = vpProject.SystemFile
    if vpProject.Vpus.Item(vpuName):
        vpProject.RemoveVpu(vpuName)
        vpProject.Save(osaFile)

    # Configure the importer.
    importSettings = vpProject.CreateNewImportSettings()
    importSettings.ImportFilePath = containerPath
    if xcpPort:
        importSettings.XcpPort = xcpPort
    if buildPath:
        importSettings.BuildDirectoryPath = buildPath
    importSettings.EnableDebugBuild = debug
    if gcc:
        importSettings.BoardName = "HostPC32"
        importSettings.CompilerName = "GCC"

    buildResult = None
    try:
        # Run the importer and build VPU.
        buildResult = vpProject.Import(importSettings)
        CopyBuildLog(osaFile, vpuName)
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


def BuildSicForVeos(vpProject, sicPath="Untitled.sic", buildPath=None, xcpPort=None):
    """
    Import a Simulink Implementation Container (SIC) and build it for VEOS.
    Note, that the OSA file is saved and reopened during the build process.
    Therefore existing COM objects for VEOS Player project elements become invalid.
    """

    # Check preconditions.
    if not os.path.exists(sicPath):
        raise Exception("SIC does not exist at path: %s" % sicPath)
    sicFileName = os.path.basename(sicPath)
    (vpuName, sicExt) = os.path.splitext(sicFileName)
    if sicExt.lower() != ".sic":
        raise Exception("Name of SIC file %s does not end with '.sic'" % sicFileName)
    osaFile = vpProject.SystemFile
    if vpProject.Vpus.Item(vpuName):
        vpProject.RemoveVpu(vpuName)
        vpProject.Save(osaFile)

    # Configure the SIC importer.
    sicImportSettings = vpProject.CreateNewImportSettings()
    sicImportSettings.ImportFilePath = sicPath
    if xcpPort:
        sicImportSettings.XcpPort = xcpPort
    if buildPath:
        sicImportSettings.BuildDirectoryPath = buildPath

    buildResult = None
    try:
        # Run the SIC importer and build VPU.
        buildResult = vpProject.Import(sicImportSettings)
        CopyBuildLog(osaFile, vpuName)
        buildStatus = buildResult.BuildStatus
        if Isa(buildStatus, "int"):
            buildStatus = VpEnums.BuildStatusEnum(buildStatus)
    except Exception:
        buildStatus = VpEnums.BuildStatusEnum.Invalid

    # Check the build status.
    if buildStatus == VpEnums.BuildStatusEnum.Valid:
        print("Build finished with status VALID")
    else:
        # Print build output and throw exception.
        if buildResult != None:
            print("Output of build: \n\n " + buildResult.BuildOutput)
        print("*** Build finished with status " + str(buildStatus))
        raise Exception("Build of %s aborted with status %s" % (sicFileName, buildStatus))

    return buildStatus


def ConnectToSystemDesk():
    """
    Opens a COM connection to SystemDesk and sets the Python path.
    """
    global SdApplication
    global SdEnums
    if SdApplication == None:
        print("Opening COM connection to SystemDesk")
        SdApplication = win32com.client.Dispatch("SystemDesk.Application.5.5")
        SdApplication.Visible = True
        applicationRootDir = SdApplication.ApplicationRootDir
        # Append the SystemDesk's directory for the BSW module automation to the Python search path.
        bswAutomationDir = os.path.join(SdApplication.ApplicationProgramDataDir, "Automation")
        if not sys.path.__contains__(bswAutomationDir):
            sys.path.insert(0, bswAutomationDir)
        # Append SystemDesk's scripting directory to the Python search path.
        scriptingDir = os.path.join(applicationRootDir + r"\Tools\Scripting")
        if not sys.path.__contains__(scriptingDir):
            sys.path.insert(0, scriptingDir)
        # The enum definitions are needed later.
        import SystemDeskEnums
        importlib.reload(SystemDeskEnums)
        SdEnums = SystemDeskEnums
    return SdApplication


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


def CreateArtifactDescriptor(codeDescriptor, artifactName, artifactCategory="SWSRC", fileCategory="Code.Component"):
    """
    Creates an AutosarEngineeringObject in a CodeDescriptor for a given artifact (e.g. a code file).
    """
    arEngineeringObject = codeDescriptor.ArtifactDescriptors.AddNew()
    arEngineeringObject.ShortLabel = artifactName
    arEngineeringObject.Category = artifactCategory
    if fileCategory == "Code.Component":
        swcShortName = codeDescriptor.Parent.BehaviorRef.Parent.ShortName
        arEngineeringObject.Files.Add(os.path.join(GetProjectRootDir(), "_ComponentFiles", swcShortName, artifactName))
    elif fileCategory == "Code.Shared":
        arEngineeringObject.Files.Add(os.path.join(GetProjectRootDir(), "_SharedFiles", artifactName))
    elif fileCategory == "Code.Standard":
        arEngineeringObject.Files.Add(os.path.join(GetProjectRootDir(), "_StandardFiles", artifactName))
    else:
        assert 0, "Currently this utility method does not support file category " + fileCategory
    return arEngineeringObject


def CreateConstantSpecification(arElement, initValue, constantSpecShortName=None,
                                constantSpecCategory=None, constantSpecUnit=None):
    """
    Returns a new ConstantSpecification for the given element.
    Creates an ApplicationValueSpecification using the given init value.
    The init value must be a (tuple of) numericals.
    Supported constantSpecCategorys are "VALUE", "BOOLEAN", "ARRAY", and "STRUCT".
    Returns the ConstantSpecification for the init value.
    """
    constantSpec = None
    if IsNumerical(initValue):
        # Create a new ConstantSpecification.
        commonPackage = FindCommonPackage(arElement)
        constantsPackage = commonPackage.ArPackages.Item("ConstantSpecifications")
        if constantsPackage == None:
            constantsPackage = commonPackage.ArPackages.AddNew("ConstantSpecifications")
        if constantSpecShortName == None:
            constantSpecShortName = "CONST_" + arElement.ShortName
        constantSpec = constantsPackage.Elements.AddNewConstantSpecification(constantSpecShortName)
        SetDescription(constantSpec, GetDescription(arElement))
        # Create a value specification.
        dataType = arElement.TypeTref
        if not dataType:
            assert False, "Data type must be set for " + arElement.ShortName
        elif dataType.ElementType == "IApplicationPrimitiveDataType":
            SetApplicationPrimitiveValueSpecification(constantSpec, initValue, constantSpecCategory, constantSpecUnit)
        elif dataType.ElementType == "IApplicationArrayDataType":
            SetApplicationArrayValueSpecification(constantSpec, initValue, constantSpecCategory, constantSpecUnit)
        elif dataType.ElementType == "IApplicationRecordDataType":
            SetApplicationRecordValueSpecification(constantSpec, dataType, initValue, constantSpecCategory, constantSpecUnit)
        else:
            assert False, "Unsupported data type for NonqueuedReceiverComSpec."
    else:
        assert False, "Unsupported type of initValue. Must be numerical."
    return constantSpec


def CreateConstantSpecificationMapping(constantSpecificationMappingSet, applConstant, implConstant):
    """
    Creates a new ConstantSpecificationMapping in the ConstantSpecificationMappingSet
    for an InternalBehavior.
    """
    constantSpecificationMapping = constantSpecificationMappingSet.Mappings.AddNew()
    constantSpecificationMapping.ApplConstantRef = applConstant
    constantSpecificationMapping.ImplConstantRef = implConstant
    return constantSpecificationMapping


def CreateDataReadAccess(runnable, port, variable):
    """
    Creates an implicit data read access for a runnable.
    """
    dataReadAccess = runnable.DataReadAccesss.AddNew("DRA_" + port.ShortName + "_" + variable.ShortName)
    CreateVariableAccess(dataReadAccess, port, variable)
    return dataReadAccess


def CreateDataReceivePointByArguments(runnable, port, variable):
    """
    Creates an explicit data receive point for a runnable
    (queued or standard, depending on SwImplPolicy of variable).
    """
    dataReceivePointByArguments = runnable.DataReceivePointByArguments.AddNew("DRP_" + port.ShortName + "_" + variable.ShortName)
    CreateVariableAccess(dataReceivePointByArguments, port, variable)
    return dataReceivePointByArguments


def CreateDataReceivePointByValue(runnable, port, variable):
    """
    Creates an explicit data receive point for a runnable
    (queued or standard, depending on SwImplPolicy of variable).
    """
    dataReceivePointByValue = runnable.DataReceivePointByValues.AddNew("DRPV_" + port.ShortName + "_" + variable.ShortName)
    CreateVariableAccess(dataReceivePointByValue, port, variable)
    return dataReceivePointByValue


def CreateDataSendPoint(runnable, port, variable):
    """
    Creates an explicit data send point for a runnable
    (queued or standard, depending on SwImplPolicy of variable).
    """
    dataSendPoint = runnable.DataSendPoints.AddNew("DSP_" + port.ShortName + "_" + variable.ShortName)
    CreateVariableAccess(dataSendPoint, port, variable)
    return dataSendPoint


def CreateDataTypeMap(dataTypeMappingSet, applDataType, implDataType):
    """
    Creates a new DataTypeMap in the DataTypeMappingSet for an InternalBehavior.
    """
    dataTypeMap = dataTypeMappingSet.DataTypeMaps.AddNew()
    dataTypeMap.ApplicationDataTypeRef = applDataType
    dataTypeMap.ImplementationDataTypeRef = implDataType
    return dataTypeMap


def CreateDataWriteAccess(runnable, port, variable):
    """
    Creates an implicit data write access for a runnable.
    """
    dataWriteAccess = runnable.DataWriteAccesss.AddNew("DWA_" + port.ShortName + "_" + variable.ShortName)
    CreateVariableAccess(dataWriteAccess, port, variable)
    return dataWriteAccess


def CreateFrameTriggering(busType, physicalChannel, frame, identifier, pduTriggerings, framePortRefs):
    """
    Creates a CanFrameTriggering for the given Frame and PduTriggerings.
    Supported busTypes are "CAN", "CAN-FD", or "LIN".
    """
    if busType == "CAN":
        frameTriggering = physicalChannel.FrameTriggerings.AddNewCanFrameTriggering()
        frameTriggering.CanAddressingMode = SdEnums.CanAddressingModeTypeEnum.Extended
        frameTriggering.CanFrameRxBehavior = SdEnums.CanFrameRxBehaviorEnum.Can20
        frameTriggering.CanFrameTxBehavior = SdEnums.CanFrameTxBehaviorEnum.Can20
    elif busType == "CAN-FD":
        frameTriggering = physicalChannel.FrameTriggerings.AddNewCanFrameTriggering()
        frameTriggering.CanAddressingMode = SdEnums.CanAddressingModeTypeEnum.Extended
        frameTriggering.CanFrameRxBehavior = SdEnums.CanFrameRxBehaviorEnum.Any ## CanFd
        frameTriggering.CanFrameTxBehavior = SdEnums.CanFrameTxBehaviorEnum.CanFd
    elif busType == "LIN":
        frameTriggering = physicalChannel.FrameTriggerings.AddNewLinFrameTriggering()
        if not frame.ElementType == "ILinSporadicFrame":
            frameTriggering.LinChecksum = SdEnums.LinChecksumTypeEnum.Enhanced
    else:
        raise Exception("Unsupported type of physical channel: " + physicalChannel.ElementType)
    frameTriggering.ShortName = frame.ShortName + "Triggering"
    frameTriggering.Identifier = identifier
    frameTriggering.FrameRef = frame
    for pduTriggering in pduTriggerings:
        pduTriggeringConditional = frameTriggering.PduTriggerings.AddNew()
        pduTriggeringConditional.PduTriggeringRef = pduTriggering
    for framePortRef in framePortRefs:
        frameTriggering.FramePortRefs.Add(framePortRef)
    return frameTriggering


def CreateFrame(iSignalIPdu, frameType="CanFrame", frameShortName=None, \
    frameLength=None, startPosition=0, packingByteOrder=None):
    """
    Returns a Frame for a given ISignalIPdu.
    """
    # Set defaults for input arguments.
    if frameShortName == None:
        frameShortName = TrimEnd(iSignalIPdu.ShortName, "IPdu") + "Frame"
    if frameLength == None:
        frameLength = iSignalIPdu.Length ## [bytes]
    if packingByteOrder == None:
        packingByteOrder = iSignalIPdu.ISignalToPduMappings.Elements[0].PackingByteOrder
    # Create or get a package for new Frames.
    commonPackage = FindCommonPackage(iSignalIPdu)
    framesPackage = commonPackage.ArPackages.Item("Frames")
    if framesPackage == None:
        framesPackage = commonPackage.ArPackages.AddNew("Frames")
    # Create the Frame.
    if frameType == "CanFrame":
        frame = framesPackage.Elements.AddNewCanFrame(frameShortName)
    elif frameType == "FlexrayFrame":
        frame = framesPackage.Elements.AddNewFlexrayFrame(frameShortName)
    elif frameType == "EthernetFrame":
        frame = framesPackage.Elements.AddNewEthernetFrame(frameShortName)
    elif frameType == "LinFrame":
        frame = framesPackage.Elements.AddNewLinUnconditionalFrame(frameShortName)
    elif frameType == "LinEventTriggeredFrame":
        frame = framesPackage.Elements.AddNewLinEventTriggeredFrame(frameShortName)
    else:
        assert 0, "Currently this utility method does not support " + frameType
    SetDescription(frame, frameType + " for ISignalIPdu " + iSignalIPdu.ShortName)
    # Set Frame parameters.
    frame.FrameLength = frameLength
    pduToFrameMapping = frame.PduToFrameMappings.AddNew()
    pduToFrameMapping.PduRef = iSignalIPdu
    pduToFrameMapping.StartPosition = startPosition
    pduToFrameMapping.PackingByteOrder = packingByteOrder
    return frame


def CreateImplConstantForApplConstant(applConstant, value, lsb=None, implConstantShortName=None):
    """
    Creates an implementation constant (e.g. NumericalValueSpecification)
    for a given ApplicationConstantSpecification. Supported categories are "VALUE"
    and "BOOLEAN".
    """
    constantsPackage = FindPackage(applConstant)
    implConstant = constantsPackage.Elements.AddNewConstantSpecification()
    if implConstantShortName != None:
        implConstant.ShortName = implConstantShortName
    else:
        implConstant.ShortName = applConstant.ShortName + "_IDT"
    SetDescription(implConstant, GetDescription(applConstant))
    implConstant.Category = applConstant.Category
    if applConstant.ValueSpec.ElementType == "IApplicationValueSpecification":
        numericalValueSpec = implConstant.SetNewValueSpecNumericalValueSpecification()
        SetNumericalValueSpecification(numericalValueSpec, value, lsb)
    elif applConstant.ValueSpec.ElementType == "IArrayValueSpecification":
        arrayValueSpecification = implConstant.SetNewValueSpecArrayValueSpecification()
        index = -1
        for valueItem in value:
            index += 1
            numericalValueSpec = arrayValueSpecification.Elements.AddNewNumericalValueSpecification()
            SetNumericalValueSpecification(numericalValueSpec, valueItem, lsb)
    elif applConstant.ValueSpec.ElementType == "IRecordValueSpecification":
        recordValueSpecification = implConstant.SetNewValueSpecRecordValueSpecification()
        for index in range(0, len(applConstant.ValueSpec.Fields.Elements)):
            numericalValueSpec = recordValueSpecification.Fields.AddNewNumericalValueSpecification()
            SetNumericalValueSpecification(numericalValueSpec, value, lsb)
    else:
        assert False, "Unsupported ValueSpec for application constant."
    return implConstant


def CreateISignal(systemSignal, iSignalShortName=None):
    """
    Returns an ISignal for a given SystemSignal.
    """
    if iSignalShortName == None:
        iSignalShortName = systemSignal.ShortName + "ISignal"
    commonPackage = FindCommonPackage(systemSignal)
    iSignalsPackage = commonPackage.ArPackages.Item("ISignals")
    if iSignalsPackage == None:
        iSignalsPackage = commonPackage.ArPackages.AddNew("ISignals")
    iSignal = iSignalsPackage.Elements.AddNewISignal(iSignalShortName)
    SetDescription(iSignal, "ISignal for SystemSignal " + systemSignal.ShortName)
    iSignal.SystemSignalRef = systemSignal
    return iSignal


def CreateISignalGroup(systemSignalGroup, iSignalGroupShortName=None):
    """
    Returns an ISignal for a given SystemSignal.
    """
    if iSignalGroupShortName == None:
        iSignalGroupShortName = systemSignalGroup.ShortName + "ISignalGroup"
    commonPackage = FindCommonPackage(systemSignalGroup)
    iSignalsPackage = commonPackage.ArPackages.Item("ISignals")
    if iSignalsPackage == None:
        iSignalsPackage = commonPackage.ArPackages.AddNew("ISignals")
    iSignalGroup = iSignalsPackage.Elements.AddNewISignalGroup(iSignalGroupShortName)
    SetDescription(iSignalGroup, "ISignalGroup for SystemSignalGroup " + systemSignalGroup.ShortName)
    iSignalGroup.SystemSignalGroupRef = systemSignalGroup
    return iSignalGroup


def CreateISignalTriggering(physicalChannel, iSignalOrISignalGroup, iSignalPortRefs):
    """
    Creates an ISignalTriggering for the given ISignal.
    """
    iSignalTriggering = physicalChannel.ISignalTriggerings.AddNew(iSignalOrISignalGroup.ShortName + "Triggering")
    if iSignalOrISignalGroup.ElementType == "IISignal":
        iSignalTriggering.ISignalRef = iSignalOrISignalGroup
    elif iSignalOrISignalGroup.ElementType == "IISignalGroup":
        iSignalTriggering.ISignalGroupRef = iSignalOrISignalGroup
    else:
        raise Exception("Invalid type of parameter iSignalOrISignalGroup: " + iSignalOrISignalGroup.ElementType)
    for iSignalPortRef in iSignalPortRefs:
        iSignalTriggering.ISignalPortRefs.Add(iSignalPortRef)
    return iSignalTriggering


def CreateMemorySection(implementation, sectionName, description=None,
                        alignment=None, symbol=None, swAddrMethod=None):
    """
    Creates a memory section with the given name for an implementation.
    """
    if not implementation.ResourceConsumption:
        implementation.SetNewResourceConsumption()

    memorySection = implementation.ResourceConsumption.MemorySections.AddNew(sectionName)
    if description:
        SetDescription(memorySection, description)
    if alignment:
        memorySection.Alignment = alignment
    if symbol:
        memorySection.Symbol = symbol
    else:
        memorySection.Symbol = sectionName.upper()
    if swAddrMethod:
        memorySection.SwAddrmethodRef = swAddrMethod
    return memorySection


def CreateModeRequestTypeMap(dataTypeMappingSet, modeDeclarationGroup, implDataType):
    """
    Creates a new ModeRequestTypeMap in the DataTypeMappingSet for an InternalBehavior.
    """
    modeRequestTypeMap = dataTypeMappingSet.ModeRequestTypeMaps.AddNew()
    modeRequestTypeMap.ModeGroupRef = modeDeclarationGroup
    modeRequestTypeMap.ImplementationDataTypeRef = implDataType
    return modeRequestTypeMap


def CreateModeSwitchPoint(runnable, port):
    """
    Creates a ModeSwitchPoint for a runnable.
    """
    modeSwitchInterface = port.ProvidedInterfaceTref
    modeGroupPrototype = modeSwitchInterface.ModeGroup
    modeSwitchPoint = runnable.ModeSwitchPoints.AddNew("MSP_" + port.ShortName + "_" + modeGroupPrototype.ShortName)
    modeGroupIref = modeSwitchPoint.SetNewModeGroupIref()
    modeGroupIref.ContextPPortRef = port
    modeGroupIref.TargetModeGroupRef = modeGroupPrototype
    return modeSwitchPoint


def CreateParameterAccess(runnable, port, parameter):
    """
    Creates an parameter access for a runnable.
    """
    parameterAccess = runnable.ParameterAccesss.AddNew("CPA_" + port.ShortName + "_" + parameter.ShortName)
    accessedParameter = parameterAccess.SetNewAccessedParameter()
    parameterInSwcIref = accessedParameter.SetNewAutosarParameterIref()
    parameterInSwcIref.PortPrototypeRef = port
    parameterInSwcIref.TargetDataPrototypeRef = parameter
    return parameterAccess


def CreatePduTriggering(physicalChannel, iPdu, iSignalTriggerings, iPduPortRefs):
    """
    Creates an PduTriggering for the given IPdu and ISignalTriggerings.
    """
    pduTriggering = physicalChannel.PduTriggerings.AddNew(iPdu.ShortName + "Triggering")
    pduTriggering.IPduRef = iPdu
    for iSignalTriggering in iSignalTriggerings:
        iSignalTriggeringConditional = pduTriggering.ISignalTriggerings.AddNew()
        iSignalTriggeringConditional.ISignalTriggeringRef = iSignalTriggering
    for iPduPortRef in iPduPortRefs:
        pduTriggering.IPduPortRefs.Add(iPduPortRef)
    return pduTriggering


def CreatePerInstanceParameterAccess(runnable, localParameter):
    """
    Creates a parameter access to a SharedParameter or a PerInstanceParameter.
    """
    parameterAccess = runnable.ParameterAccesss.AddNew("PICPVA_" + localParameter.ShortName)
    accessedParameter = parameterAccess.SetNewAccessedParameter()
    accessedParameter.LocalParameterRef = localParameter
    return parameterAccess


def CreateProject(saveOldProject=False):
    """
    Closes a possibly open project in SystemDesk and creates a new one.
    BY DEFAULT, THE OLD PROJECT DATA IS NOT SAVED.
    If the parameter templateProjectName is specified, then this project is used
    as a template for the new project, i.e. the template project is opened and
    saved as Options.ProjectName.
    """
    # Close open project.
    if SdApplication.ActiveProject != None:
        SdApplication.ActiveProject.Close(saveOldProject)
    # Determine the full path of the new project file.
    projectRootDir = GetNewProjectRootDir()
    projectFile = os.path.join(projectRootDir, Options.ProjectName + ".sdp")
    # Create new SystemDesk project.
    print("Creating SystemDesk project %s" % Options.ProjectName)
    print("Using project file %s" % projectFile)
    # Create a new project.
    SdProject = SdApplication.CreateProject(projectFile)
    if SdProject == None:
        raise Exception("SystemDesk project '%s' could not be created." % projectFile)
    SdProject.Name = Options.ProjectName
    # Return the new SystemDesk Project object.
    return SdProject


def CreateReadLocalVariable(runnable, variable):
    """
    Creates a read access to an inter-runnable variable
    (implicit or explicit, depending on the inter-runnable variable definition in the internal behavior).
    """
    localVariableReadAccess = runnable.ReadLocalVariables.AddNew("IRVRA_" + variable.ShortName)
    accessedVariable = localVariableReadAccess.SetNewAccessedVariable()
    accessedVariable.LocalVariableRef = variable
    return localVariableReadAccess


def CreateRequiredArtifact(implementation, dependencyName, \
        artifactName, artifactCategory, usage=None):
    """
    Creates a DependencyOnArtifact element for a SwcImplementation.
    """
    dependencyOnArtifact = implementation.RequiredArtifacts.AddNew(dependencyName)
    if usage != None:
        dependencyOnArtifact.Usages.Add(usage)
    arEngineeringObject = dependencyOnArtifact.SetNewArtifactDescriptor()
    arEngineeringObject.ShortLabel = artifactName
    arEngineeringObject.Category = artifactCategory

    if dependencyName.lower().__contains__("dsfxp"):
        SetDescription(dependencyOnArtifact, "TargetLink fixed point library. " + \
        "Contains utility functions and macros for code generated by TargetLink.")
        arEngineeringObject.RevisionLabels.Add("1.3.2")
        arEngineeringObject.Files.Add("<ProjectDir>\\_SharedFiles\\DsFxpLib+Vs1.3.2.pkc")
    else:
        arEngineeringObject.Files.Add(artifactName)

    return dependencyOnArtifact


def CreateSenderReceiverToSignalGroupMapping(arSystem, swcs, port, dataElement, systemSignalGroup=None):
    """
    Creates a SenderReceiverToSignalGroup mapping for the given composite type.
    """
    if systemSignalGroup:
        sr2sgMapping = arSystem.CreateSenderReceiverToSignalGroupMapping( \
            swcs, port, dataElement)
        sr2sgMapping.SignalGroupRef = systemSignalGroup
        sr2sgMapping.SetNewTypeMapping()
        if dataElement.TypeTref.ElementType == "IApplicationArrayDataType":
            srPrimitiveElementMappings = sr2sgMapping.TypeMapping.ArrayElementMappings.Elements
        elif dataElement.TypeTref.ElementType == "IApplicationRecordDataType":
            srPrimitiveElementMappings = sr2sgMapping.TypeMapping.RecordElementMappings.Elements
        else:
            raise Exception("Utilities.CreateSenderReceiverToSignalGroupMapping() not implemented for " + dataElement.ElementType)
        # Map the composite elements to system signals.
        systemSignals = systemSignalGroup.SystemSignalRefs.Elements
        for index, srPrimitiveElementMapping in enumerate(srPrimitiveElementMappings):
            srPrimitiveElementMapping.SystemSignalRef = systemSignals[index]
    else:
        sr2sgMapping = arSystem.CreateSenderReceiverToSignalGroupMapping(swcs, port, dataElement)
    return sr2sgMapping


def CreateSharedParameterAccess(runnable, localParameter):
    """
    Creates a parameter access to a SharedParameter or a PerInstanceParameter.
    """
    parameterAccess = runnable.ParameterAccesss.AddNew("SCPVA_" + localParameter.ShortName)
    accessedParameter = parameterAccess.SetNewAccessedParameter()
    accessedParameter.LocalParameterRef = localParameter
    return parameterAccess


def CreateStandardMemorySection(implementation, sectionName):
    """
    Creates a standard memory section. Valid section names are
        ("CODE", "CONST_xxx", "VAR_NOINIT_xxx", "INTERNAL_VAR_xxx",)
    where xxx is one of BOOLEAN, 8BIT, 16BIT, 32BIT, UNSPECIFIED.
    """
    # Determine the alignment.
    sectionNameUpper = sectionName.upper()
    if sectionNameUpper.endswith("_BOOLEAN"):
        alignment = 8
        swAddrMethodName = sectionNameUpper[0:len(sectionNameUpper)-8]
        alignmentDesc = ", boolean, aligned to 8 bit"
    elif sectionNameUpper.endswith("_8"):
        alignment = 8
        swAddrMethodName = sectionNameUpper[0:len(sectionNameUpper)-2]
        alignmentDesc = ", aligned to 8 bit"
    elif sectionNameUpper.endswith("_8BIT"):
        alignment = 8
        swAddrMethodName = sectionNameUpper[0:len(sectionNameUpper)-5]
        alignmentDesc = ", aligned to 8 bit"
    elif sectionNameUpper.endswith("_16"):
        alignment = 16
        swAddrMethodName = sectionNameUpper[0:len(sectionNameUpper)-3]
        alignmentDesc = ", aligned to 16 bit"
    elif sectionNameUpper.endswith("_16BIT"):
        alignment = 16
        swAddrMethodName = sectionNameUpper[0:len(sectionNameUpper)-6]
        alignmentDesc = ", aligned to 16 bit"
    elif sectionNameUpper.endswith("_32"):
        alignment = 32
        swAddrMethodName = sectionNameUpper[0:len(sectionNameUpper)-3]
        alignmentDesc = ", aligned to 32 bit"
    elif sectionNameUpper.endswith("_32BIT"):
        alignment = 32
        swAddrMethodName = sectionNameUpper[0:len(sectionNameUpper)-6]
        alignmentDesc = ", aligned to 32 bit"
    elif sectionNameUpper.endswith("_PTR"):
        alignment = 32
        swAddrMethodName = sectionNameUpper[0:len(sectionNameUpper)-4]
        alignmentDesc = ", pointer, alignment 32 bit"
    elif sectionNameUpper.endswith("_UNSPECIFIED"):
        alignment = None
        swAddrMethodName = sectionNameUpper[0:len(sectionNameUpper)-12]
        alignmentDesc = ", alignment unspecified"
    else:
        alignment = None
        swAddrMethodName = sectionNameUpper
        alignmentDesc = ""

    # Determine the description text and SwAddrMethod.
    if swAddrMethodName.startswith("VAR"):
        description = "Global or static variables (RAM%s)" % alignmentDesc
    elif swAddrMethodName.startswith("INTERNAL_VAR"):
        description = "Global or static variables which are accessible by a calibration system (RAM%s)" % alignmentDesc
    elif swAddrMethodName.startswith("CONST"):
        description = "Global or static constants (ROM%s)" % alignmentDesc
    elif swAddrMethodName.startswith("CALIB"):
        description = "Global or static calibration parameters (Flash%s)" % alignmentDesc
    elif swAddrMethodName.startswith("CONFIG_DATA"):
        description = "Global or static configuration data (Flash%s)" % alignmentDesc
    elif swAddrMethodName.startswith("CODE"):
        description = "Global or static functions (ROM%s)" % alignmentDesc
    else:
        raise Exception("Not implemented in this script. Section name: " + sectionName)
    swAddrMethod = GetElementByPath("/SharedElements/SwAddrMethods/" + swAddrMethodName)

    # Now create the standard memory section.
    memorySection = CreateMemorySection(implementation, sectionName, description, alignment, sectionNameUpper, swAddrMethod)
    return memorySection


def CreateSynchronousServerCallPoint(runnable, port, operation):
    """
    Creates a synchronous server call point for a runnable.
    """
    serverCallPoint = runnable.ServerCallPoints.AddNewSynchronousServerCallPoint("SSCP_" + port.ShortName + "_" + operation.ShortName)
    serverCallPoint.Timeout = 1.0e38 ## Mandatory property in strict schema. Required for tresos.
    operationIref = serverCallPoint.SetNewOperationIref()
    operationIref.ContextRPortRef = port
    operationIref.TargetRequiredOperationRef = operation


def CreateVariableAccess(dataAccess, port, variable):
    """
    Connects a DataReadAccess, DataWriteAccess, ... to a variable at a port.
    """
    accessedVariable = dataAccess.SetNewAccessedVariable()
    variableInSwcIref = accessedVariable.SetNewAutosarVariableIref()
    variableInSwcIref.PortPrototypeRef = port
    variableInSwcIref.TargetDataPrototypeRef = variable
    return accessedVariable


def CreateWrittenLocalVariable(runnable, variable):
    """
    Creates a write access to an inter-runnable variable
    (implicit or explicit, depending on the inter-runnable variable definition in the internal behavior).
    """
    localVariableWriteAccess = runnable.WrittenLocalVariables.AddNew("IRVWA_" + variable.ShortName)
    accessedVariable = localVariableWriteAccess.SetNewAccessedVariable()
    accessedVariable.LocalVariableRef = variable
    return localVariableWriteAccess


def DeleteElementByPath(arQualifiedPath):
    """
    Deletes the element at the given AUTOSAR path, if it exists. The path may
    start with a project name or ECU configuration name separated by a
    colon ':', which restricts the search to the given scope.
    Examples:
        /AUTOSAR_Platform/ImplemmentationTypes/uint32_least
        ControllerEcuConfiguration:/AUTOSAR_Platform/ImplemmentationTypes/uint32_least
    """
    element = GetElementByPath(arQualifiedPath)
    if element:
        element.Delete()


def DisconnectFromSystemDesk():
    """
    Closes a COM connection to SystemDesk and disposes the sdApplication object.
    """
    global SdApplication
    if SdApplication != None:
        SdApplication.Quit()
        SdApplication = None


def DisconnectFromVeosPlayer():
    """
    Closes a COM connection to the VEOS Player and disposes the vpApplication object.
    """
    global VpApplication
    if VpApplication != None:
        VpApplication.Quit()
        VpApplication = None


def ExportSwcContainer(swc, autosarExportVersion=None):
    """
    Exports the SWC container for the given software component.
    Example1: ExportSwcContainer(mySwc)
    Example2: ExportSwcContainer(mySwc, "AUTOSAR 4.4.0")
    """

    # Configure the ContainerManager object.
    projectRootDir = GetProjectRootDir()
    containerSet = os.path.join(projectRootDir, Options.ProjectName + ".cts")
    catalogFile = os.path.join(".", "_ComponentFiles", swc.ShortName, swc.ShortName + ".ctlg")
    swc.ContainerManager.ContainerSet = containerSet
    swc.ContainerManager.CatalogFile = catalogFile
    if autosarExportVersion:
        swc.ContainerManager.AutosarExportVersion = autosarExportVersion

    # Perform the export in batch mode (without dialogs).
    try:
        oldBatchMode = SdApplication.BatchMode
        SdApplication.BatchMode = True
        swc.ContainerManager.Export()
        SdApplication.BatchMode = oldBatchMode
    except Exception as e:
        SdApplication.BatchMode = False
        ##print repr(e)
        raise Exception(e)


def FindAncestor(arElement, ancestorElementType):
    """
    Returns the first parent of the arElement with the given ElementType.
    """
    parent = arElement.Parent
    while(True):
        if parent == None:
            return None
        elif parent.ElementType == ancestorElementType:
            return parent
        else:
            parent = parent.Parent


def FindCommonPackage(arElement):
    """
    Returns the AUTOSAR package for a component or for common elements.
    """
    subPackageNames = (
        "ApplicationDataTypes",
        "CommunicationClusters",
        "CompuMethods",
        "ConstantSpecificationMappingSets",
        "ConstantSpecifications",
        "DataConstrs",
        "DataTypeMappingSets",
        "EcuInstances",
        "Frames",
        "ImplementationDataTypes",
        "ISignals",
        "Pdus",
        "PhysicalDimensions",
        "PortInterfaces",
        "ModeDeclarationGroups",
        "SwAddrMethods",
        "SwComponentTypes",
        "SwcImplementations",
        "SystemSignals",
        "Systems",
        "Units",)
    parent = arElement.Parent
    while(True):
        if parent == None:
            return None
        elif parent.ElementType == "IARPackage":
            # Skip subpackages for standard elements.
            if subPackageNames.__contains__(parent.ShortName):
                parent = parent.Parent
            else:
                # Ok, package found.
                return parent
        else:
            parent = parent.Parent


def FindModuleConfiguration(ecuConfiguration, moduleName):
    """
    Searches a module configuration in the given EcuConfiguration.
    """
    ecucValues = ecuConfiguration.EcucValueCollection.EcucValues
    for moduleConfigurationRefConditional in ecucValues.Elements:
        moduleConfiguration = moduleConfigurationRefConditional.EcucModuleConfigurationValuesRef
        if moduleConfiguration.ShortName == moduleName:
            return moduleConfiguration
    return None

def FindNextPositionInTask(rteConfiguration, osTask):
    """
    Searches all runnables and BSW main functions which are mapped on a given task
    and returns the next free position in the task.
    """
    positionInTask = 0

    if rteConfiguration != None:
        # Iterate all RTE event mappings.
        for swcInstance in rteConfiguration.RteSwComponentInstances.Elements:
            for rteEventToTaskMapping in swcInstance.RteEventToTaskMappings.Elements:
                if rteEventToTaskMapping.RteMappedToTaskRef:
                    if rteEventToTaskMapping.RteMappedToTaskRef.ShortName == osTask.ShortName:
                        if rteEventToTaskMapping.RtePositionInTask >= positionInTask:
                            positionInTask = rteEventToTaskMapping.RtePositionInTask + 1
        # Iterate all BSW event mappings.
        for bswModuleInstance in rteConfiguration.RteBswModuleInstances.Elements:
            for bswEventToTaskMapping in bswModuleInstance.RteBswEventToTaskMappings.Elements:
                if bswEventToTaskMapping.RteBswMappedToTaskRef:
                    if bswEventToTaskMapping.RteBswMappedToTaskRef.ShortName == osTask.ShortName:
                        if bswEventToTaskMapping.RteBswPositionInTask >= positionInTask:
                            positionInTask = bswEventToTaskMapping.RteBswPositionInTask + 1

    return positionInTask


def FindOsTaskForBswMainFunction(rteConfiguration, bswModuleName, bswMainFunctionName):
    """
    Returns the OsTask which contains the given BSW main function.
    """

    # Iterate all main function mappings.
    for bswModuleInstance in rteConfiguration.RteBswModuleInstances.Elements:
        for bswEventToTaskMapping in bswModuleInstance.RteBswEventToTaskMappings.Elements:
            bswEvent = bswEventToTaskMapping.RteBswEventRef
            bswModuleDescription = bswEvent.Parent.Parent
            if bswModuleDescription.ShortName == bswModuleName:
                if bswEvent.StartsOnEventRef.ShortName == bswMainFunctionName:
                    return bswEventToTaskMapping.RteBswMappedToTaskRef
                elif bswMainFunctionName.startswith(bswModuleName + "_"):
                    ## HACK: Remove this.
                    bswMainFunctionNameWithoutPrefix = bswMainFunctionName[len(bswModuleName)+1:]
                    if bswEvent.StartsOnEventRef.ShortName == bswMainFunctionNameWithoutPrefix:
                        return bswEventToTaskMapping.RteBswMappedToTaskRef
                elif bswEvent.StartsOnEventRef.ShortName.startswith(bswModuleName + "_"):
                    ## HACK: Remove this.
                    bswStartsOnEventWithoutPrefix = bswEvent.StartsOnEventRef.ShortName[len(bswModuleName)+1:]
                    if bswStartsOnEventWithoutPrefix == bswMainFunctionName:
                        return bswEventToTaskMapping.RteBswMappedToTaskRef

    # BSW main function is not mapped to an OsTask.
    return None


def FindOsAlarmForOsTask(osTask):
    """
    Returns the OsTask which contains the given BSW main function.
    """
    osConfiguration = osTask.Parent

    # Iterate all OsAlarms.
    for osAlarm in osConfiguration.OsAlarms.Elements:
        if osAlarm.OsAlarmAction.OsAlarmActivateTaskRef.ShortName == osTask.ShortName:
            return osAlarm

    # BSW main function is not mapped to an OsTask.
    return None


def FindPackage(element):
    """
    Returns the AUTOSAR package where an element is defined.
    """
    return FindAncestor(element, "IARPackage")


def FindSwcPrototype(ecuConfiguration, swcType):
    """
    Returns the (first) software component prototype in the ECU flat view which
    references the given software component.
    """
    ecuFlatView = ecuConfiguration.EcuExtractSystem.RootSwCompositionPrototype
    swComposition = ecuFlatView.SoftwareCompositionTref
    for swcPrototype in swComposition.Components.Elements:
        if swcPrototype.TypeTref == swcType:
            return swcPrototype
    return None


def GetBswPluginDir(bswModuleName):
    """
    Returns the plugin directory for a given BSW module
    (where the ARXML description is stored, e.g. Autosar.NvM.arxml).
    """
    bswPluginDir = os.path.join("Bsw", "Modules", bswModuleName, "Config", "dSPACE")
    bswPluginDirAbsolute = os.path.join(SdApplication.ApplicationRootDir, bswPluginDir)
    if not os.path.exists(bswPluginDirAbsolute):
        raise Exception("The plugin directory '" + bswPluginDirAbsolute + "' does not exist.")
    return os.path.join("<InstallationDir>", bswPluginDir)


def GetDataElementIRef(rootComposition, componentName, portName, dataElementName):
    """
    Returns an instance reference for a data element at a given port of a component.
    The instance reference is a triple of [swc, port, de].
    """
    swc = rootComposition.Components.Item(componentName)
    port = swc.TypeTRef.Ports.Item(portName)
    portInterface = port.GetInterface()
    de = portInterface.DataElements.Item(dataElementName)
    return [swc, port, de]


def GetDescription(arElement):
    """
    Returns the description of an AUTOSAR element.
    """
    descriptionText = ""
    try:
        if arElement.Desc:
            for mlText in arElement.Desc.L2.Elements:
                descriptionText = descriptionText + mlText.MixedContent.ConcateToString()
    except Exception:
        dummy = 1
    return descriptionText


def GetEcuComPortInstance(commConnector, commPortPostfix):
    """
    Returns an EcuCommPortInstance for a given CommConnector. To determine the name
    of the EcuCommPortInstance, the following steps are performed:
        1) Take the name of the communication connector   e.g. "ControllerCanConnector"
        2) Remove trailing string "Connector"             e.g. "ControllerCan"
        3) Append the given commPortPostfix to the name   e.g. "ControllerCan" + "ISignalPortOut"
    """
    commConnectorPrefix = TrimEnd(commConnector.ShortName, "Connector")
    commPort = commConnector.EcuCommPortInstances.Item(commConnectorPrefix + commPortPostfix)
    return commPort


def GetElementByPath(arQualifiedPath):
    """
    Returns the element at the given AUTOSAR path. The path may start with a
    project name or ECU configuration name separated by a colon ':', which
    restricts the search to the given scope.
    Examples:
        /AUTOSAR_Platform/ImplemmentationTypes/uint8
        ControllerEcuConfiguration:/AUTOSAR_Platform/ImplemmentationTypes/uint8
    """

    # Split the scope from the AUTOSAR path.
    arQualifiedPathItems = arQualifiedPath.split(':')
    if len(arQualifiedPathItems) <= 1:
        # Normal path without scope. Search the element at the given path.
        arRoot = SdApplication.ActiveProject.RootAutosar
        if arRoot.ArPackages.Count == 0:
            return None
        firstPackage = arRoot.ArPackages.Elements[0]
        elements = firstPackage.GetElementsByARPath(arQualifiedPath)
        if bool(elements):
            return elements[0]
        else:
            return None

    # Given path contains scope.
    scope = arQualifiedPathItems[0]
    arPath = arQualifiedPathItems[1]

    # Determine the root element for the search.
    arRoot = None
    if scope == SdApplication.ActiveProject.Name:
        arRoot = SdApplication.ActiveProject.RootAutosar
    else:
        for ecuConfiguration in SdApplication.ActiveProject.EcuConfigurations.Elements:
            if ecuConfiguration.Name == scope:
                arRoot = ecuConfiguration.RootAutosar
                break
    if not arRoot:
        return None

    # Search the element at the given path.
    element = None
    # Iterate all path items. List begins with "" if the path is rooted.
    for arPathItem in arPath.split('/'):
        if arPathItem == "":
            # Iteration starts with root.
            element = arRoot
        else:
            # Try to find a subpackage with the given name.
            subpackage = element.ArPackages.Item(arPathItem)
            if subpackage == None:
                if element == arRoot:
                    # Element is root package. Path below root could not be resolved.
                    return None
                # Element is a package. Return element in package.
                element = element.Elements.Item(arPathItem)
                return element
            else:
                # Continue with subpackage.
                element = subpackage
    return element


def GetNoUnit():
    """
    Returns /AUTOSAR_PhysicalUnits/Units/NoUnit, if it exists.
    """
    return GetElementByPath("/AUTOSAR_PhysicalUnits/Units/NoUnit")


def GetNewProjectRootDir():
    """
    Returns the default directory for a new project.
    """
    # Use the script directory as the default root directory for the new project.
    #projectRootDir = 'D:\Cicd Automation\System_Desk_Automation\Shruthe\SystemDesk_Automation_Build\Cicd_Implementation\Virtual_ECU\SystemDeskProject\Production_Asw_Sim_Rte'
    global path
    #return path
    #scriptDir = os.path.abspath(os.path.dirname(sys.argv[0]))
    scriptDir = path
    scriptDirBaseName = os.path.basename(scriptDir)
    print(scriptDirBaseName)
    if scriptDirBaseName == "Production_Asw_Rte_Sim":
        # Place the project in the parent folder of this script.
        print('scriptdirbasename is inter')
        #projectRootDir = os.path.dirname(scriptDir)
        projectRootDir = scriptDir
    else:
        # Place the project in the same directory where the script resides.
        projectRootDir = scriptDir
    return projectRootDir


def GetOperationIRef(rootComposition, componentName, portName, operationName):
    """
    Returns an instance reference for an operation at a given port of a component.
    The instance reference is a triple of [swc, port, op].
    """
    swc = rootComposition.Components.Item(componentName)
    port = swc.TypeTRef.Ports.Item(portName)
    portInterface = port.GetInterface()
    op = portInterface.Operations.Item(operationName)
    return [swc, port, op]


def GetOrCreateApplicationArrayDataType(arElement):
    """
    Returns the ApplicationPrimitiveDataType for an ArElement.
    A new ApplicationPrimitiveDataType is created if it does not already exist.
    """
    adt = arElement.TypeTref
    if adt == None:
        commonPackage = FindCommonPackage(arElement)
        adtPackage = commonPackage.ArPackages.Item("ApplicationDataTypes")
        if adtPackage == None:
            adtPackage = commonPackage.ArPackages.AddNew("ApplicationDataTypes")
        adt = adtPackage.Elements.AddNewApplicationArrayDataType(arElement.ShortName)
        adt.Category = "ARRAY"
        SetDescription(adt, "ApplicationDataType for " + arElement.ShortName)
        arElement.TypeTref = adt
        adt.SetNewElement()
        adt.Element.ShortName = arElement.ShortName + "_ELEMENT"
        SetDescription(adt.Element, "Element of " + arElement.ShortName)
    return adt


def GetOrCreateApplicationPrimitiveDataType(arElement, adtShortName=None):
    """
    Returns the ApplicationPrimitiveDataType for an ArElement.
    A new ApplicationPrimitiveDataType is created if it does not already exist.
    """
    adt = arElement.TypeTref
    if not adtShortName:
        adtShortName = arElement.ShortName
    if adt == None:
        commonPackage = FindCommonPackage(arElement)
        adtPackage = commonPackage.ArPackages.Item("ApplicationDataTypes")
        if adtPackage == None:
            adtPackage = commonPackage.ArPackages.AddNew("ApplicationDataTypes")
        adt = adtPackage.Elements.Item(adtShortName)
        if not adt:
            adt = adtPackage.Elements.AddNewApplicationPrimitiveDataType(adtShortName)
            adt.Category = arElement.Category
            SetDescription(adt, "ApplicationDataType for " + arElement.ShortName)
        arElement.TypeTref = adt
    return adt


def GetOrCreateCompuMethod(arElement, shortName=None):
    """
    Returns the CompuMethod for an ArElement.
    A new CompuMethod is created if it does not already exist.
    """
    swDataDefProps = arElement.GetOrCreateSwDataDefProps()
    compuMethod = swDataDefProps.CompuMethodRef
    if compuMethod == None:
        commonPackage = FindCommonPackage(arElement)
        cmPackage = commonPackage.ArPackages.Item("CompuMethods")
        if cmPackage == None:
            cmPackage = commonPackage.ArPackages.AddNew("CompuMethods")
        if shortName != None:
            compuMethod = cmPackage.Elements.Item(shortName)
            if compuMethod == None:
                compuMethod = cmPackage.Elements.AddNewCompuMethod(shortName)
        else:
            compuMethod = cmPackage.Elements.AddNewCompuMethod(arElement.ShortName)
        SetDescription(compuMethod, "CompuMethod for " + arElement.ShortName)
        swDataDefProps.TrySetCompuMethodRef(compuMethod)
    return compuMethod


def GetOrCreateConstantSpecificationMappingSet(element):
    """
    Returns the ConstantSpecificationMappingSet for an InternalBehavior or a ParameterSwComponentType.
    A new ConstantSpecificationMappingSet is created if it does not already exist.
    """
    # Early return if a ConstantSpecificationMappingSet already exists.
    if element.ElementType == "IParameterSwComponentType":
        if bool(element.ConstantMappingRefs.Elements):
            return element.ConstantMappingRefs.Elements[0]
    else:
        if bool(element.ConstantValueMappingRefs.Elements):
            return element.ConstantValueMappingRefs.Elements[0]

    # Create ConstantMappingSpecificationSet below the package of the SWC.
    swcPackage = FindPackage(element)
    csmsPackage = swcPackage.ArPackages.Item("ConstantSpecificationMappingSets")
    if csmsPackage == None:
        csmsPackage = swcPackage.ArPackages.AddNew("ConstantSpecificationMappingSets")
    csms = csmsPackage.Elements.AddNewConstantSpecificationMappingSet()
    SetDescription(csms, "ConstantSpecificationMappingSet for " + element.ShortName)

    # Add the ConstantMappingSpecificationSet to the given element.
    if element.ElementType == "IParameterSwComponentType":
        csms.ShortName = element.ShortName + "_ConstantSpecificationMappingSet"
        element.ConstantMappingRefs.Add(csms)
    else:
        csms.ShortName = element.Parent.ShortName + "_ConstantSpecificationMappingSet"
        element.ConstantValueMappingRefs.Add(csms)
    return csms


def GetOrCreateDataConstr(arElement, shortName=None):
    """
    Returns the DataConstr for an ArElement.
    A new DataConstr is created if it does not already exist.
    """
    swDataDefProps = arElement.GetOrCreateSwDataDefProps()
    dataConstr = swDataDefProps.DataConstrRef
    if dataConstr == None:
        ## commonPackage = FindCommonPackage(arElement)
        ## dcPackage = commonPackage.ArPackages.Item("DataConstrs")
        ## if dcPackage == None:
        ##     dcPackage = commonPackage.ArPackages.AddNew()
        ##     dcPackage.ShortName = "DataConstrs"
        dcPackage = FindPackage(arElement)
        if shortName != None:
            dataConstr = dcPackage.Elements.Item(shortName)
            if dataConstr == None:
                dataConstr = dcPackage.Elements.AddNewDataConstr(shortName)
        else:
            dataConstr = dcPackage.Elements.AddNewDataConstr("DC_" + arElement.ShortName)
        swDataDefProps.TrySetDataConstrRef(dataConstr)
    return dataConstr


def GetOrCreateDataTypeMappingSet(element):
    """
    Returns the DataTypeMappingSet for an InternalBehavior or for a ParameterSwComponentType.
    A new DataTypeMappingSet is created if it does not already exist.
    """
    # Early return if a DataTypeMappingSet already exists.
    if bool(element.DataTypeMappingRefs.Elements):
        return element.DataTypeMappingRefs.Elements[0]
    # Create DataTypeMappingSet below the package of the SWC.
    swcPackage = FindPackage(element)
    dtmsPackage = swcPackage.ArPackages.Item("DataTypeMappingSets")
    if dtmsPackage == None:
        dtmsPackage = swcPackage.ArPackages.AddNew("DataTypeMappingSets")
    dtms = dtmsPackage.Elements.AddNewDataTypeMappingSet()
    if element.ElementType == "IParameterSwComponentType":
        dtms.ShortName = element.ShortName + "_DataTypeMappingSet"
    else:
        # ElementType is e.g. ISwcInternalBehavior.
        dtms.ShortName = element.Parent.ShortName + "_DataTypeMappingSet"
    SetDescription(dtms, "DataTypeMappingSet for " + element.ShortName)
    element.DataTypeMappingRefs.Add(dtms)
    return dtms


def GetOrCreateImplementationDataType(adt, idtShortName=None, idtElementType=None):
    """
    Creates an ImplementationDataType for a given ApplicationDataType.
    """
    if idtShortName == None:
        idtShortName = adt.ShortName + "_IDT"

    commonPackage = FindCommonPackage(adt)
    idtPackage = commonPackage.ArPackages.Item("ImplementationDataTypes")
    if idtPackage == None:
        idtPackage = commonPackage.ArPackages.AddNew("ImplementationDataTypes")
    idt = idtPackage.Elements.Item(idtShortName)
    if idt != None:
        return idt
    idt = idtPackage.Elements.AddNewImplementationDataType(idtShortName)
    SetDescription(idt, "ImplementationDataType for ApplicationDataType " + adt.ShortName)
    idt.Category = adt.Category
    if adt.ElementType == "IApplicationArrayDataType":
        subElement = idt.SubElements.AddNew(adt.Element.ShortName)
        subElement.Category = "TYPE_REFERENCE"
        SetDescription(subElement, "Implementation for ApplicationArrayDataType element " + adt.ShortName + "." + subElement.ShortName)
        subElement.ArraySizeSemantics = SdEnums.ArraySizeSemanticsEnum.FixedSize
        subElement.SetNewArraySize().SetValue(adt.Element.MaxNumberOfElements.MixedContent.Elements[0].StringElement)
        swDataDefProps = subElement.GetOrCreateSwDataDefProps()
        swDataDefProps.TrySetImplementationDataTypeRef(idtElementType)
    elif adt.ElementType == "IApplicationRecordDataType":
        index = -1
        for recordElement in adt.Elements.Elements:
            index += 1
            subElement = idt.SubElements.AddNew(recordElement.ShortName)
            subElement.Category = "TYPE_REFERENCE"
            SetDescription(subElement, "Implementation for ApplicationRecordDataType element " + adt.ShortName + "." + subElement.ShortName)
            swDataDefProps = GetOrCreateSwDataDefProps(subElement)
            swDataDefProps.TrySetImplementationDataTypeRef(idtElementType[index])
    elif adt.ElementType != "IApplicationPrimitiveDataType":
        raise Exception("Invalid ElementType of parameter adt: " + adt.ElementType)
    if not adt.ContainerFileRef.IsDefaultFile:
        adt.ContainerFileRef.Add(idt)
    return idt


def GetOrCreateInitValueConstant(arElement, constantSpecShortName=None):
    """
    Returns the InitValue for an ArElement.
    A new Constant is created if it does not already exist.
    """
    initValue = arElement.InitValue
    if initValue == None:
        if (constantSpecShortName == None):
            constantSpecShortName = "CONST_" + arElement.ShortName
        commonPackage = FindCommonPackage(arElement)
        constantsPackage = commonPackage.ArPackages.Item("ConstantSpecifications")
        if constantsPackage == None:
            constantsPackage = commonPackage.ArPackages.AddNew("ConstantSpecifications")
        constantSpec = constantsPackage.Elements.AddNewConstantSpecification(constantSpecShortName)
        SetDescription(constantSpec, GetDescription(arElement))
        constantRef = arElement.SetNewInitValueConstantReference()
        ##constantRef.ShortLabel = constantSpec.ShortName
        constantRef.ConstantRef = constantSpec
    else:
        constantSpec = initValue.ConstantRef
    return constantSpec


def GetOrCreatePackage(arPath):
    """
    Returns the ArPackage at the given AUTOSAR path.
    Creates a new ArPackage if it does not exist.
    """
    arPathItems = arPath.split('/')
    arRoot = SdApplication.ActiveProject.RootAutosar
    arPackage = None
    for arPathItem in arPathItems:
        if arPathItem == "":
            arPackage = arRoot
        else:
            subpackage = arPackage.ArPackages.Item(arPathItem)
            if subpackage == None:
                subpackage = arPackage.ArPackages.AddNew(arPathItem)
            arPackage = subpackage
    return arPackage


def GetOrCreateSwcImplementation(element, shortName=None):
    """
    Returns the SwcImplementation for a SwComponentType or SwcInternalBehavior.
    """

    if element.ElementType == "ISwcInternalBehavior":
        swcInternalBehavior = element
        swc = swcInternalBehavior.Parent.Parent
    else:
        swc = element
        swcInternalBehavior = swc.InternalBehavior.Elements[0]

    # Default name is <SwcName>Implementation.
    if not shortName:
        shortName = swc.ShortName + "Implementation"

    # Create SwcImplementation below the package of the SWC.
    implPackage = FindCommonPackage(element)
    ##swcPackage = FindCommonPackage(element)
    ##implPackage = swcPackage.ArPackages.Item("SwcImplementations")
    ##if implPackage == None:
    ##    implPackage = swcPackage.ArPackages.AddNew("SwcImplementations")
    swcImplementation = implPackage.Elements.AddNewSwcImplementation(shortName)
    swcImplementation.BehaviorRef = swcInternalBehavior

    return swcImplementation


def GetOrCreateSwDataDefProps(arElement):
    """
    Returns the SwDataDefPropsConditional for an AUTOSAR element.
    """
    if arElement.ElementType == "ISystemSignal":
        if arElement.PhysicalProps == None:
            swddp = arElement.SetNewPhysicalProps()
        else:
            swddp = arElement.PhysicalProps
    elif arElement.ElementType == "IISignal":
        if arElement.NetworkRepresentationProps == None:
            swddp = arElement.SetNewNetworkRepresentationProps()
        else:
            swddp = arElement.NetworkRepresentationProps
    else:
        if arElement.SwDataDefProps == None:
            swddp = arElement.SetNewSwDataDefProps()
        else:
            swddp = arElement.SwDataDefProps

    if swddp.SwDataDefPropsVariants.Count > 0:
        return swddp.SwDataDefPropsVariants.Elements[0]
    else:
        return swddp.SwDataDefPropsVariants.AddNew()


def GetProjectRootDir():
    """
    Returns the project root directory (where the SDP file is stored).
    """
    global path
    sdProject = SdApplication.ActiveProject
    if sdProject == None:
        return GetNewProjectRootDir()
    projectRootDir = os.path.dirname(sdProject.File)
    #projectRootDir = path
    return projectRootDir


def GetVpuPort(vpu, pathItems):
    """
    Returns the VpuPort object at the given path.
    The path must be specified as a string array.
    """
    if Isa(pathItems, "str"):
        return vpu.VpuPorts.Item(pathItems)
    elif len(pathItems) == 1:
        return vpu.VpuPorts.Item(pathItems[0])
    else:
        vpuPortGroup = vpu.VpuPortGroups.Item(pathItems[0])
        for pathItem in pathItems[1:len(pathItems)-1]:
            vpuPortGroup = vpuPortGroup.Item(pathItem)
        vpuPort = vpuPortGroup.Item(pathItems[len(pathItems)-1])
        return vpuPort


def ImportA2lFile(internalBehavior, a2lFilePath):
    """
    Imports an A2L file at a given InternalBehavior. The RTE generator collects
    the A2L Variables from all InternalBehaviors on an ECU and merges it into
    the ECU A2L file.
    """

    # Expand relative path name if necessary.
    if not os.path.isabs(a2lFilePath):
        a2lFilePath = os.path.join(GetProjectRootDir(), a2lFilePath)

    # Get an import manager and import the A2L file.
    a2lVariableImporter = internalBehavior.VariableImporter
    a2lVariableImporter.Filename = a2lFilePath
    oldBatchMode = SdApplication.BatchMode
    SdApplication.BatchMode = True
    try:
        status = a2lVariableImporter.Import()
    except Exception:
        status = False
    finally:
        SdApplication.BatchMode = oldBatchMode
    assert status, "A2L import from file %s failed. See Message Browser." % a2lFilePath


##def ExportA2lFile(self, ecuConfiguration, a2lFilePath, \
##    a2lTemplatePath = None, mapFileType = None, mapFilePath = None):
##    """
##    Exports an A2L file for a given ECU configuration. The mapFileType
##    and mapFilePath must be specified to export an A2L file with address
##    information.
##    """
##
##    # Expand relative path name if necessary.
##    if not os.path.isabs(a2lFilePath):
##        a2lFilePath = os.path.join(self.ProjectRootDir, a2lFilePath)
##
##    # Get an export manager and export the A2L file.
##    a2lExportManager = ecuConfiguration.Export
##    a2lExportManager.Format = "A2L"
##    a2lExportManager.FileName = a2lFilePath
##    if mapFileType and mapFilePath:
##        a2lExportManager.AddAdvancedProperty("CreateAddressInfo", True)
##        a2lExportManager.AddAdvancedProperty("MapFileType", mapFileType)
##        a2lExportManager.AddAdvancedProperty("MapFilePath", mapFilePath)
##    if a2lTemplatePath:
##        a2lExportManager.AddAdvancedProperty("A2LTemplate", a2lTemplatePath)
##    try:
##        oldBatchMode = Application.BatchMode
##        Application.BatchMode = True
##        status = a2lExportManager.Do()
##    except:
##        status = False
##    Application.BatchMode = oldBatchMode
##    assert status, "A2L export to file %s failed. See Message Browser." % a2lFilePath
##
##    ## print a2lExportManager.SupportedAdvancedProperties
##    ## 'CreateAddressInfo'    Boolean
##    ## 'MapFileType'          String, e.g. 'Microsoft_standard_32bit' for OffSim VPU DLLs.
##    ## 'MapFilePath'          String
##    ## 'A2LTemplate',         String
##    ## 'ProjectName',         String
##    ## 'ModuleName',          String
##    ## 'Enable_Project/ProjectLibrary/SwcFolder1/SwcName1/IbName1'   String
##    ## 'Enable_Project/ProjectLibrary/SwcFolder2/SwcName2/IbName2'   String


def ImportAutosarFiles(fileNames, elementSelections="/",
                       importDiagrams=True, optionShowImportDialog=False):
    """
    Imports the selected AUTOSAR file(s).
    Relative path names refer to the project root directory.
    """

    # Convert file names to a list.
    if not Isa(fileNames, 'list'):
        fileNames = [fileNames]
    # Convert element selections to a list.
    if not Isa(elementSelections, 'list'):
        elementSelections = [elementSelections]

    # Iterate all files.
    for fileNameItem in fileNames:
        SdProject = SdApplication.ActiveProject
        # Configure an ImportExportFile in SystemDesk
        print("Importing " + fileNameItem)
        importExportFile = SdProject.ImportExportFiles.Add(fileNameItem)
        importExportFile.AddNewElementsToConfiguration = True
        importExportFile.ExportDiagrams = importDiagrams
        importExportFile.ImportDiagrams = importDiagrams
        importExportFile.ImportAllElements = True
        importExportFile.ShowImportDialog = optionShowImportDialog

        # Now import the file.
        success = importExportFile.Import()
        if success == False:
            raise Exception("AUTOSAR import failed")


def ImportAutosarFilesAtProject(fileNames, elementSelections="/",
                                importDiagrams=True, optionShowImportDialog=False):
    """
    Imports the selected AUTOSAR file(s) using the (De-)Serializer at the Project element.
    Relative path names refer to the project root directory.
    """
    SdProject = SdApplication.ActiveProject

    # Convert file names to a list.
    if not Isa(fileNames, 'list'):
        fileNames = [fileNames]
    # Convert element selections to a list.
    if not Isa(elementSelections, 'list'):
        elementSelections = [elementSelections]

    # Write console message(s).
    for fileNameItem in fileNames:
        print("Importing " + fileNameItem)

    # Configure the importer.
    importSettings = SdProject.Serializer.GetNewImportSettings()
    importSettings.SetFilePaths(fileNames)
    importSettings.SetElementSelection(elementSelections)
    importSettings.ImportDiagrams = importDiagrams
    importSettings.SelectAllElements = True
    importSettings.ShowImportDialog = optionShowImportDialog
    importSettings.CheckSettings()

    # Now import the file(s).
    success = SdProject.Serializer.Import(importSettings)
    if success == False:
        raise Exception("AUTOSAR import failed")


def ImportSwcContainer(containerName, containerSet=None):
    """
    Imports the SWC container for the given software component.
    Example:
        ImportSwcContainer("MyComponent", "D:\\MyProject\\MyProject.cts")
    """

    # Configure the ContainerManager object.
    catalogFile = os.path.join(".", "_ComponentFiles", containerName, containerName + ".ctlg")
    containerManager = SdApplication.ActiveProject.ContainerManager
    containerManager.ContainerSet = containerSet
    containerManager.CatalogFile = catalogFile

    # Perform the import in batch mode (without dialogs).
    try:
        oldBatchMode = SdApplication.BatchMode
        SdApplication.BatchMode = True
        containerManager.Import()
        SdApplication.BatchMode = oldBatchMode
    except Exception as e:
        SdApplication.BatchMode = False
        ##print repr(e)
        raise Exception(e)

def OpenProject(saveOldProject=False):
    """
    Closes a possibly open project in SystemDesk and opens another one.
    BY DEFAULT, THE OLD PROJECT DATA IS NOT SAVED.
    """

    # Close open project.
    if SdApplication.ActiveProject != None:
        SdApplication.ActiveProject.Close(saveOldProject)

    # Determine the full path of the new project file.
    projectRootDir = GetNewProjectRootDir()
    projectFile = os.path.join(projectRootDir, Options.ProjectName + ".sdp")

    if not os.path.exists(projectFile):
        print("*** SystemDesk project %s does not exist." % projectFile)
        return

    # Open the project in batch mode. Catch exceptions.
    oldBatchMode = SdApplication.BatchMode
    SdApplication.BatchMode = True
    try:
        print("\nOpening SystemDesk project %s" % projectFile)
        SdApplication.OpenProject(projectFile)
    except Exception as e:
        SdApplication.BatchMode = oldBatchMode
        raise Exception(e)
    finally:
        SdApplication.BatchMode = oldBatchMode


def RemoveFromContainerFile(containerFile, arQualifiedPath):
    """
    Removes the element at the given AUTOSAR path from the given container file,
    if it exists. The path may start with a project name or ECU configuration
    name separated by a colon ':', which restricts the search to the given scope.
    Examples:
        /AUTOSAR_Platform/ImplemmentationTypes/uint32_least
        ControllerEcuConfiguration:/AUTOSAR_Platform/ImplemmentationTypes/uint32_least
    """
    element = GetElementByPath(arQualifiedPath)
    if element:
        containerFile.Remove(element)


def RunBswPlugin(bswModuleConfiguration, command, arg=None):
    """
    Invokes a BSW plugin command in batch mode for the given module configuration.
    """
    messages = None
    try:
        oldBatchMode = SdApplication.BatchMode
        SdApplication.BatchMode = True
        if not arg:
            messages = bswModuleConfiguration.RunBswPlugin(command)
        else:
            messages = bswModuleConfiguration.RunBswPluginWithArgs(command, arg)
        SdApplication.BatchMode = oldBatchMode
    except:
        SdApplication.BatchMode = False
        raise Exception("Command '%s' aborted with exception." % command)
    ThrowIfError(messages, command)


def SaveProject(sdpFile=None):
    """
    Saves the active SystemDesk project.
    """
    SdProject = SdApplication.ActiveProject
    if not SdProject:
        print("No SystemDesk project open")
        return

    if sdpFile:
        print("Saving SystemDesk project as %s" % sdpFile)
        SdProject.SaveAs(sdpFile)
    else:
        print("Saving SystemDesk project %s" % SdProject.Repository)
        SdProject.Save()


def SetApplicationArrayValueSpecification(constantSpec, values, elementCategory=None, unit=None):
    """
    Creates an ApplicationArrayValueSpecification for a ConstantSpecification and
    sets the given value. Supported elementCategories are "VALUE" and "BOOLEAN".
    """
    constantSpec.Category = "ARRAY"
    arrayValueSpecification = constantSpec.SetNewValueSpecArrayValueSpecification()
    index = -1
    for value in values:
        if elementCategory == None:
            if IsNumerical(value):
                elementCategory = "VALUE"
            elif IsBoolean(value):
                elementCategory = "BOOLEAN"
            else:
                raise Exception("SetApplicationArrayValueSpecification() not implemented for values of " + str(value.__class__))
        index += 1
        applValueSpecification = arrayValueSpecification.Elements.AddNewApplicationValueSpecification()
        applValueSpecification.Category = elementCategory
        ## applValueSpecification.ShortLabel = "Element" + str(index)
        swValueCont = applValueSpecification.SetNewSwValueCont()
        if unit != None:
            swValueCont.UnitRef = unit
        else:
            swValueCont.UnitRef = GetNoUnit()
        if value != None:
            swValuesPhys = swValueCont.SetNewSwValuesPhys()
            if (value == int(value)):
                swValuesPhys.V.Add(int(value))  ## use "42" instead of "42.0"
            else:
                swValuesPhys.V.Add(value)


def SetApplicationPrimitiveValueSpecification(constantSpec, value, category=None, unit=None):
    """
    Creates an ApplicationValueSpecification for a ConstantSpecification and
    sets the given value. Supported categories are "VALUE" and "BOOLEAN".
    """
    if category == None:
        if IsNumerical(value):
            category = "VALUE"
        elif IsBoolean(value):
            category = "BOOLEAN"
        else:
            raise Exception("SetApplicationPrimitiveValueSpecification() not implemented for values of " + str(value.__class__))
    constantSpec.Category = category
    applValueSpecification = constantSpec.SetNewValueSpecApplicationValueSpecification()
    applValueSpecification.Category = category
    swValueCont = applValueSpecification.SetNewSwValueCont()
    if unit != None:
        swValueCont.UnitRef = unit
    else:
        swValueCont.UnitRef = GetNoUnit()
    if value != None:
        swValuesPhys = swValueCont.SetNewSwValuesPhys()
        if (value == int(value)):
            swValuesPhys.V.Add(int(value))  ## use "42" instead of "42.0"
        else:
            swValuesPhys.V.Add(value)


def SetApplicationRecordValueSpecification(constantSpec, recordDataType, value, elementCategory=None, unit=None):
    """
    Creates an ApplicationRecordValueSpecification for a ConstantSpecification and
    sets the given value. Supported elementCategories are "VALUE" and "BOOLEAN".
    """
    if elementCategory == None:
        if IsNumerical(value):
            elementCategory = "VALUE"
        elif IsBoolean(value):
            elementCategory = "BOOLEAN"
        else:
            raise Exception("SetApplicationRecordValueSpecification() not implemented for values of " + str(value.__class__))
    constantSpec.Category = "STRUCTURE"
    recordValueSpecification = constantSpec.SetNewValueSpecRecordValueSpecification()
    for recordElement in recordDataType.Elements.Elements:
        applValueSpecification = recordValueSpecification.Fields.AddNewApplicationValueSpecification()
        ###SetDescription(applValueSpecification, GetDescription(recordElement))
        applValueSpecification.Category = elementCategory
        applValueSpecification.ShortLabel = recordElement.ShortName
        swValueCont = applValueSpecification.SetNewSwValueCont()
        if unit != None:
            swValueCont.UnitRef = unit
        else:
            swValueCont.UnitRef = GetNoUnit()
        if value != None:
            swValuesPhys = swValueCont.SetNewSwValuesPhys()
            if (value == int(value)):
                swValuesPhys.V.Add(int(value))  ## use "42" instead of "42.0"
            else:
                swValuesPhys.V.Add(value)


def SetArrayElementType(arrayType, elementType, maxNumberOfElements=None):
    """
    Sets the properties of an element of an array type.
    """
    arrayType.Element.Category = "VALUE"
    arrayType.Element.TypeTref = elementType
    arrayType.Element.ArraySizeSemantics = SdEnums.ArraySizeSemanticsEnum.FixedSize
    if maxNumberOfElements != None:
        arrayType.SetMaxNumberOfElements(str(maxNumberOfElements))


def SetDataIref(arElement, contextRPort, dataElement):
    """
    Sets the instance reference to a data element at an AUTOSAR element.
    """
    dataIref = arElement.SetNewDataIref()
    dataIref.ContextRPortRef = contextRPort
    dataIref.TargetDataElementRef = dataElement


def SetDescription(arElement, description):
    """
    Creates a description for an AUTOSAR element.
    """
    if description in (None, ""):
        if arElement.Desc != None:
            arElement.Desc.Delete()
    else:
        desc = arElement.SetNewDesc()
        mlText = desc.L2.AddNew()
        mlText.MixedContent.AddStringContent(description)
        mlText.L = SdEnums.LEnum.ForAll


def SetInitValue(arElement, initValue=None, initValueConstantShortName=None, initValueCategory=None, initValueUnit=None):
    """
    Creates an initial value for the given AUTOSAR element.
    The initValue can be specified as a numerical value or as an existing ConstantSpecification.
    Supported InitValueCategories are "VALUE" and "BOOLEAN".
    Returns the ConstantSpecification for the init value.
    """
    initValueConstantSpec = None
    if initValue != None:
        if IsNumerical(initValue) or IsBoolean(initValue):
            # Create a new ConstantSpecification.
            if initValueConstantShortName == None:
                initValueConstantShortName = "CONST_" + arElement.ShortName
            initValueConstantSpec = GetOrCreateInitValueConstant(arElement, initValueConstantShortName)
            SetDescription(initValueConstantSpec, "Initvalue constant for " + arElement.ShortName)
            dataType = arElement.TypeTref
            if not dataType:
                assert False, "Data type must be set for " + arElement.ShortName
            elif dataType.ElementType == "IApplicationPrimitiveDataType":
                SetApplicationPrimitiveValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationArrayDataType":
                SetApplicationArrayValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationRecordDataType":
                SetApplicationRecordValueSpecification(initValueConstantSpec, dataType, initValue, initValueCategory, initValueUnit)
            else:
                assert False, "Unsupported data type for " + arElement.ShortName
        elif initValue.ElementType == "IConstantSpecification":
            # Use the existent ConstantSpecification.
            initValueConstantSpec = initValue
            constantReference = arElement.SetNewInitValueConstantReference()
            constantReference.ConstantRef = initValueConstantSpec
        else:
            assert False, "Unsupported type of initValue."
    return initValueConstantSpec


def SetInternalConstraints(dataConstr, lowerLimit=None, upperLimit=None, constrLevel=0):
    """
    Sets the (hard) internal constraints for a data constraint.
    """
    dataConstrRule = dataConstr.DataConstrRules.AddNew()
    if constrLevel != None:
        dataConstrRule.ConstrLevel = constrLevel
    internalConstrs = dataConstrRule.SetNewInternalConstrs()
    if lowerLimit != None:
        lowLimit = internalConstrs.SetNewLowerLimit()
        lowLimit.MixedContent.AddStringContent(Value2Str(lowerLimit))
        lowLimit.IntervalType = SdEnums.IntervalTypeEnum.Closed
    if upperLimit != None:
        upLimit = internalConstrs.SetNewUpperLimit()
        upLimit.MixedContent.AddStringContent(Value2Str(upperLimit))
        upLimit.IntervalType = SdEnums.IntervalTypeEnum.Closed


def SetInvalidationPolicy(interface, dataElement, handleInvalid):
    """
    Creates a new InvalidationPolicy element for the given data element.
    """
    invalidationPolicy = interface.InvalidationPolicys.AddNew()
    invalidationPolicy.DataElementRef = dataElement
    invalidationPolicy.HandleInvalid = handleInvalid


def SetISignalIPduCyclicTiming(iSignalIpdu, \
    transmissionMode=True, minimumDelay=None, \
    timePeriod=None, timeOffset=None, \
    transmissionModeConditions=None):
    """
    Sets an event controlled IpduTiming for a ISignalIpdu.
    """
    iPduTiming = iSignalIpdu.IPduTimingSpecifications.AddNew()
    if minimumDelay != None:
        iPduTiming.MinimumDelay = minimumDelay
    transmissionModeDeclaration = iPduTiming.SetNewTransmissionModeDeclaration()
    if transmissionMode == True:
        transmissionModeTiming = transmissionModeDeclaration.SetNewTransmissionModeTrueTiming()
    else:
        transmissionModeTiming = transmissionModeDeclaration.SetNewTransmissionModeFalseTiming()
    cyclicTiming = transmissionModeTiming.SetNewCyclicTiming()
    if timePeriod != None:
        cyclicTiming.SetNewTimePeriod().Value = timePeriod
    if timeOffset != None:
        cyclicTiming.SetNewTimeOffset().Value = timeOffset
    if transmissionModeConditions != None:
        for transmissionModeCondition in transmissionModeConditions:
            transmissionModeCond = transmissionModeDeclaration.TransmissionModeConditions.AddNew()
            transmissionModeCond.SetNewDataFilter()
            transmissionModeCond.DataFilter.DataFilterType = transmissionModeCondition[0]
            transmissionModeCond.ISignalInIPduRef = transmissionModeCondition[1]
    return iPduTiming


def SetISignalIPduEventControlledTiming(iSignalIpdu, \
    transmissionMode=True, minimumDelay=None, \
    numOfRepetitions=None, repetitionPeriod=None, \
    transmissionModeConditions=None):
    """
    Sets an event controlled IpduTiming for a ISignalIpdu.
    """
    iPduTiming = iSignalIpdu.IPduTimingSpecifications.AddNew()
    if minimumDelay != None:
        iPduTiming.MinimumDelay = minimumDelay
    transmissionModeDeclaration = iPduTiming.SetNewTransmissionModeDeclaration()
    if transmissionMode == True:
        transmissionModeTiming = transmissionModeDeclaration.SetNewTransmissionModeTrueTiming()
    else:
        transmissionModeTiming = transmissionModeDeclaration.SetNewTransmissionModeFalseTiming()
    eventControlledTiming = transmissionModeTiming.SetNewEventControlledTiming()
    if numOfRepetitions != None:
        eventControlledTiming.NumberOfRepetitions = numOfRepetitions
    if repetitionPeriod != None:
        eventControlledTiming.SetNewRepetitionPeriod().Value = repetitionPeriod
    if transmissionModeConditions != None:
        for transmissionModeCondition in transmissionModeConditions:
            transmissionModeCond = transmissionModeDeclaration.TransmissionModeConditions.AddNew()
            transmissionModeCond.SetNewDataFilter()
            transmissionModeCond.DataFilter.DataFilterType = transmissionModeCondition[0]
            transmissionModeCond.ISignalInIPduRef = transmissionModeCondition[1]
    return iPduTiming


def SetLinearCompuMethod(compuMethod, lsb=1.0, offset=0.0):
    """
    Creates a CompuMethod with Category LINEAR.
    """
    compuMethod.Category = 'LINEAR'
    compuMethod.UnitRef = GetNoUnit()
    compuInternalToPhys = compuMethod.SetNewCompuInternalToPhys()
    compuScale = compuInternalToPhys.CompuScales.AddNew()
    compuRationalCoeffs = compuScale.SetNewCompuRationalCoeffs()
    compuNumerator = compuRationalCoeffs.SetNewCompuNumerator()
    compuNumeratorCoeff0 = compuNumerator.V.AddNew()
    compuNumeratorCoeff1 = compuNumerator.V.AddNew()
    compuDenominator = compuRationalCoeffs.SetNewCompuDenominator()
    compuDenominatorCoeff0 = compuDenominator.V.AddNew()
    if lsb >= 1.0:
        compuNumeratorCoeff0.MixedContent.AddStringContent("%g"%offset)
        compuNumeratorCoeff1.MixedContent.AddStringContent("%g"%lsb)
        compuDenominatorCoeff0.MixedContent.AddStringContent("1")
    else:
        compuNumeratorCoeff0.MixedContent.AddStringContent("%g"%(offset/lsb))
        compuNumeratorCoeff1.MixedContent.AddStringContent("1")
        compuDenominatorCoeff0.MixedContent.AddStringContent("%g"%(1.0/lsb))


def SetModeSwitchReceiverComSpec(port, enhancedModeApi=None, supportsAsynchronousModeSwitch=None):
    """
    Creates a ModeSwitchReceiverComSpec and sets the proerties EnhancedModeApi and
    SupportsAsynchronousModeSwitch.
    """
    modeSwitchReceiverComSpec = port.RequiredComSpecs.AddNewModeSwitchReceiverComSpec()
    modeSwitchReceiverComSpec.ModeGroupRef = port.RequiredInterfaceTref.ModeGroup
    if (enhancedModeApi != None):
        modeSwitchReceiverComSpec.EnhancedModeApi = enhancedModeApi
    if (supportsAsynchronousModeSwitch != None):
        modeSwitchReceiverComSpec.SupportsAsynchronousModeSwitch = supportsAsynchronousModeSwitch


def SetModeSwitchSenderComSpec(port, queueLength=1, timeout=None):
    """
    Creates a ModeSwitchSenderComSpec and sets the queue length.
    The queue length must be a positive integer (>= 1).
    If a timeout is given, then an appropriate ModeSwitchAckRequest is also created.
    """
    modeSwitchSenderComSpec = port.ProvidedComSpecs.AddNewModeSwitchSenderComSpec()
    modeSwitchSenderComSpec.ModeGroupRef = port.ProvidedInterfaceTref.ModeGroup
    modeSwitchSenderComSpec.QueueLength = str(queueLength)
    if timeout != None:
        modeSwitchAckRequest = modeSwitchSenderComSpec.SetNewModeSwitchedAck()
        modeSwitchAckRequest.Timeout = timeout


def SetNumericalValueSpecification(numericalValueSpec, value, lsb=None):
    """
    Assigns a value to the given NumericalValueSpecification.
    If an LSB is given, then the given value is converted to the internal representation
    using implValue = round(value/lsb).
    """
    if (lsb != None):
        value = round(value/lsb)
    numericalValueVariationPoint = numericalValueSpec.SetNewValue()
    numericalValueVariationPoint.MixedContent.AddStringContent(Value2Str(value))



def SetNonqueuedReceiverComSpec(port, dataElement, \
    initValue=None, initValueConstantShortName=None, initValueCategory=None, initValueUnit=None):
    """
    Creates a NonqueuedReceiverComSpec and sets the InitValue for the given data element.
    The initValue can be specified as a numerical value or as an existing ConstantSpecification.
    Supported InitValueCategories are "VALUE" and "BOOLEAN".
    Returns the ConstantSpecification for the init value.
    """
    initValueConstantSpec = None
    nonqueuedReceiverComSpec = port.RequiredComSpecs.AddNewNonqueuedReceiverComSpec()
    nonqueuedReceiverComSpec.DataElementRef = dataElement
    nonqueuedReceiverComSpec.AliveTimeout = 0.0
    nonqueuedReceiverComSpec.HandleOutOfRange = SdEnums.HandleOutOfRangeEnum.NONE
    nonqueuedReceiverComSpec.HandleTimeoutType = SdEnums.HandleTimeoutEnum.NONE
    nonqueuedReceiverComSpec.EnableUpdate = False
    nonqueuedReceiverComSpec.HandleNeverReceived = False
    nonqueuedReceiverComSpec.SetNewUsesEndToEndProtection()
    nonqueuedReceiverComSpec.UsesEndToEndProtection.SetValue(False)
    if initValue != None:
        if IsNumerical(initValue):
            # Create a new ConstantSpecification.
            if initValueConstantShortName == None:
                initValueConstantShortName = "CONST_" + port.ShortName + "_" + dataElement.ShortName
            initValueConstantSpec = GetOrCreateInitValueConstant(nonqueuedReceiverComSpec, initValueConstantShortName)
            SetDescription(initValueConstantSpec, "Initvalue constant for data element " + dataElement.ShortName)
            dataType = dataElement.TypeTref
            if not dataType:
                assert False, "Data type must be set for " + port.ShortName + "." + dataElement.ShortName
            elif dataType.ElementType == "IApplicationPrimitiveDataType":
                SetApplicationPrimitiveValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationArrayDataType":
                SetApplicationArrayValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationRecordDataType":
                SetApplicationRecordValueSpecification(initValueConstantSpec, dataType, initValue, initValueCategory, initValueUnit)
            else:
                assert False, "Unsupported data type for NonqueuedReceiverComSpec."
        elif initValue.ElementType == "IConstantSpecification":
            # Use the existent ConstantSpecification.
            initValueConstantSpec = initValue
            constantReference = nonqueuedReceiverComSpec.SetNewInitValueConstantReference()
            constantReference.ConstantRef = initValueConstantSpec
        else:
            assert False, "Unsupported type of initValue."
    return initValueConstantSpec


def SetNonqueuedSenderComSpec(port, dataElement, \
    initValue=None, initValueConstantShortName=None, initValueCategory=None, initValueUnit=None):
    """
    Creates a NonqueuedSenderComSpec and sets the InitValue for the given data element.
    The initValue can be specified as a numerical value or as an existing ConstantSpecification.
    Supported InitValueCategories are "VALUE" and "BOOLEAN".
    Returns the ConstantSpecification for the init value.
    """
    initValueConstantSpec = None
    nonqueuedSenderComSpec = port.ProvidedComSpecs.AddNewNonqueuedSenderComSpec()
    nonqueuedSenderComSpec.DataElementRef = dataElement
    nonqueuedSenderComSpec.HandleOutOfRange = SdEnums.HandleOutOfRangeEnum.NONE
    nonqueuedSenderComSpec.SetNewUsesEndToEndProtection()
    nonqueuedSenderComSpec.UsesEndToEndProtection.SetValue(False)
    if initValue != None:
        if IsNumerical(initValue):
            # Create a new ConstantSpecification.
            if initValueConstantShortName == None:
                initValueConstantShortName = "CONST_" + port.ShortName + "_" + dataElement.ShortName
            initValueConstantSpec = GetOrCreateInitValueConstant(nonqueuedSenderComSpec, initValueConstantShortName)
            SetDescription(initValueConstantSpec, "Initvalue constant for data element " + dataElement.ShortName)
            dataType = dataElement.TypeTref
            if not dataType:
                assert False, "Data type must be set for " + port.ShortName + "." + dataElement.ShortName
            elif dataType.ElementType == "IApplicationPrimitiveDataType":
                SetApplicationPrimitiveValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationArrayDataType":
                SetApplicationArrayValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationRecordDataType":
                SetApplicationRecordValueSpecification(initValueConstantSpec, dataType, initValue, initValueCategory, initValueUnit)
            else:
                assert False, "Unsupported data type for NonqueuedSenderComSpec"
        elif initValue.ElementType == "IConstantSpecification":
            # Use the existent ConstantSpecification.
            initValueConstantSpec = initValue
            constantReference = nonqueuedSenderComSpec.SetNewInitValueConstantReference()
            constantReference.ConstantRef = initValueConstantSpec
        else:
            assert False, "Unsupported type of initValue."
    return initValueConstantSpec


def SetNvProvideRequireComSpec(prPort, nvData, \
    initValue=None, initValueConstantShortName=None, initValueCategory=None, initValueUnit=None):
    """
    Creates a NvProvideComSpec and a NvRequireComSpec and sets the InitValue for the given data nvData.
    The same ConstantSpecification is used for initialization of the RamBlock, RomBlock, and R-Port.
    The initValue can be specified as a numerical value or as an existing ConstantSpecification.
    Supported InitValueCategories are "VALUE" and "BOOLEAN".
    Returns the ConstantSpecification for the init value.
    """
    initValueConstantSpec = None
    nvRequireComSpec = prPort.RequiredComSpecs.AddNewNvRequireComSpec()
    nvRequireComSpec.VariableRef = nvData
    nvProvideComSpec = prPort.ProvidedComSpecs.AddNewNvProvideComSpec()
    nvProvideComSpec.VariableRef = nvData
    if initValue != None:
        if IsNumerical(initValue):
            # Create a new ConstantSpecification.
            if initValueConstantShortName == None:
                initValueConstantShortName = "CONST_" + prPort.ShortName + "_" + nvData.ShortName
            initValueConstantSpec = GetOrCreateInitValueConstant(nvRequireComSpec, initValueConstantShortName)
            SetDescription(initValueConstantSpec, "Initvalue constant for NvData element " + nvData.ShortName)
            dataType = nvData.TypeTref
            if not dataType:
                assert False, "Data type must be set for " + prPort.ShortName + "." + nvData.ShortName
            elif dataType.ElementType == "IApplicationPrimitiveDataType":
                SetApplicationPrimitiveValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationArrayDataType":
                SetApplicationArrayValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationRecordDataType":
                SetApplicationRecordValueSpecification(initValueConstantSpec, dataType, initValue, initValueCategory, initValueUnit)
            else:
                assert False, "Unsupported data type for NvRequireComSpec."
        elif initValue.ElementType == "IConstantSpecification":
            # Use the existent ConstantSpecification.
            initValueConstantSpec = initValue
            constantReference = nvRequireComSpec.SetNewInitValueConstantReference()
            constantReference.ConstantRef = initValueConstantSpec
        else:
            assert False, "Unsupported type of initValue."
        # Set the same init value for the RAM and ROM block.
        ramBlockConstantReference = nvProvideComSpec.SetNewRamBlockInitValueConstantReference()
        ramBlockConstantReference.ConstantRef = initValueConstantSpec
        romBlockConstantReference = nvProvideComSpec.SetNewRomBlockInitValueConstantReference()
        romBlockConstantReference.ConstantRef = initValueConstantSpec
    return initValueConstantSpec


def SetNvRequireComSpec(port, nvData, \
    initValue=None, initValueConstantShortName=None, initValueCategory=None, initValueUnit=None):
    """
    Creates a NvRequireComSpec and sets the InitValue for the given data nvData.
    The initValue can be specified as a numerical value or as an existing ConstantSpecification.
    Supported InitValueCategories are "VALUE" and "BOOLEAN".
    Returns the ConstantSpecification for the init value.
    """
    initValueConstantSpec = None
    nvRequireComSpec = port.RequiredComSpecs.AddNewNvRequireComSpec()
    nvRequireComSpec.VariableRef = nvData
    if initValue != None:
        if IsNumerical(initValue):
            # Create a new ConstantSpecification.
            if initValueConstantShortName == None:
                initValueConstantShortName = "CONST_" + port.ShortName + "_" + nvData.ShortName
            initValueConstantSpec = GetOrCreateInitValueConstant(nvRequireComSpec, initValueConstantShortName)
            SetDescription(initValueConstantSpec, "Initvalue constant for data element " + nvData.ShortName)
            dataType = nvData.TypeTref
            if not dataType:
                assert False, "Data type must be set for " + port.ShortName + "." + nvData.ShortName
            elif dataType.ElementType == "IApplicationPrimitiveDataType":
                SetApplicationPrimitiveValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationArrayDataType":
                SetApplicationArrayValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationRecordDataType":
                SetApplicationRecordValueSpecification(initValueConstantSpec, dataType, initValue, initValueCategory, initValueUnit)
            else:
                assert False, "Unsupported data type for NvRequireComSpec."
        elif initValue.ElementType == "IConstantSpecification":
            # Use the existent ConstantSpecification.
            initValueConstantSpec = initValue
            constantReference = nvRequireComSpec.SetNewInitValueConstantReference()
            constantReference.ConstantRef = initValueConstantSpec
        else:
            assert False, "Unsupported type of initValue."
    return initValueConstantSpec


def SetParameterProvideComSpec(port, parameter, \
    initValue=None, initValueConstantShortName=None, initValueCategory="VALUE", initValueUnit=None):
    """
    Creates a ParameterProvideComSpec and sets the InitValue for the given parameter.
    Supported InitValueCategories are "VALUE", "BOOLEAN", and "ARRAY"
    """
    initValueConstantSpec = None
    parameterProvideComSpec = port.ProvidedComSpecs.AddNewParameterProvideComSpec()
    parameterProvideComSpec.ParameterRef = parameter
    if initValue != None:
        if IsNumerical(initValue):
            # Create a new ConstantSpecification.
            if initValueConstantShortName == None:
                initValueConstantShortName = "CONST_" + port.ShortName + "_" + parameter.ShortName
            initValueConstantSpec = GetOrCreateInitValueConstant(parameterProvideComSpec, initValueConstantShortName)
            SetDescription(initValueConstantSpec, "Initvalue constant for parameter " + parameter.ShortName)
            dataType = parameter.TypeTref
            if not dataType:
                assert False, "Data type must be set for " + port.ShortName + "." + parameter.ShortName
            if dataType.ElementType == "IApplicationPrimitiveDataType":
                SetApplicationPrimitiveValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationArrayDataType":
                SetApplicationArrayValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationRecordDataType":
                SetApplicationRecordValueSpecification(initValueConstantSpec, dataType, initValue, initValueCategory, initValueUnit)
            else:
                assert False, "Unsupported data type for ParameterProvideComSpec"
        elif initValue.ElementType == "IConstantSpecification":
            # Use the existent ConstantSpecification.
            initValueConstantSpec = initValue
            constantReference = parameterProvideComSpec.SetNewInitValueConstantReference()
            constantReference.ConstantRef = initValueConstantSpec
        else:
            assert False, "Unsupported type of initValue."
    return initValueConstantSpec


def SetParameterRequireComSpec(port, parameter, \
    initValue=None, initValueConstantShortName=None, initValueCategory="VALUE", initValueUnit=None):
    """
    Creates a ParameterRequireComSpec and sets the InitValue for the given parameter.
    Supported InitValueCategories are "VALUE", "BOOLEAN", and "ARRAY"
    """
    initValueConstantSpec = None
    parameterRequireComSpec = port.RequiredComSpecs.AddNewParameterRequireComSpec()
    parameterRequireComSpec.ParameterRef = parameter
    if initValue != None:
        if IsNumerical(initValue):
            # Create a new ConstantSpecification.
            if initValueConstantShortName == None:
                initValueConstantShortName = "CONST_" + port.ShortName + "_" + parameter.ShortName
            initValueConstantSpec = GetOrCreateInitValueConstant(parameterRequireComSpec, initValueConstantShortName)
            SetDescription(initValueConstantSpec, "Initvalue constant for parameter " + parameter.ShortName)
            dataType = parameter.TypeTref
            if not dataType:
                assert False, "Data type must be set for " + port.ShortName + "." + parameter.ShortName
            if dataType.ElementType == "IApplicationPrimitiveDataType":
                SetApplicationPrimitiveValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationArrayDataType":
                SetApplicationArrayValueSpecification(initValueConstantSpec, initValue, initValueCategory, initValueUnit)
            elif dataType.ElementType == "IApplicationRecordDataType":
                SetApplicationRecordValueSpecification(initValueConstantSpec, dataType, initValue, initValueCategory, initValueUnit)
            else:
                assert False, "Unsupported data type for ParameterRequireComSpec"
        elif initValue.ElementType == "IConstantSpecification":
            # Use the existent ConstantSpecification.
            initValueConstantSpec = initValue
            constantReference = parameterRequireComSpec.SetNewInitValueConstantReference()
            constantReference.ConstantRef = initValueConstantSpec
        else:
            assert False, "Unsupported type of initValue."
    return initValueConstantSpec


def SetPhysicalConstraints(dataConstr, lowerLimit=None, upperLimit=None, constrLevel=0):
    """
    Sets the (hard) physical constraints for a data constraint.
    """
    dataConstrRule = dataConstr.DataConstrRules.AddNew()
    if constrLevel != None:
        dataConstrRule.ConstrLevel = constrLevel
    physConstrs = dataConstrRule.SetNewPhysConstrs()
    if lowerLimit != None:
        lowLimit = physConstrs.SetNewLowerLimit()
        lowLimit.MixedContent.AddStringContent(Value2Str(lowerLimit))
        lowLimit.IntervalType = SdEnums.IntervalTypeEnum.Closed
    if upperLimit != None:
        upLimit = physConstrs.SetNewUpperLimit()
        upLimit.MixedContent.AddStringContent(Value2Str(upperLimit))
        upLimit.IntervalType = SdEnums.IntervalTypeEnum.Closed


def SetPimInitValue(perInstanceMemory, initValue, constantSpecShortName=None,
                    constantSpecCategory=None, constantSpecUnit=None):
    """
    Returns a new ConstantSpecification for the given element.
    Creates an ApplicationValueSpecification using the given init value.
    The init value must be a (tuple of) numericals.
    Supported constantSpecCategorys are "VALUE", "BOOLEAN", "ARRAY", and "STRUCT".
    Returns the ConstantSpecification for the init value.
    """
    constantSpec = None
    if IsNumerical(initValue):
        # Create a new ConstantSpecification.
        constantSpec = GetOrCreateInitValueConstant(perInstanceMemory, constantSpecShortName)
        SetDescription(constantSpec, "Initvalue constant for PerInstanceMemory " + perInstanceMemory.ShortName)
        # Create a value specification.
        dataType = perInstanceMemory.TypeTref
        if not dataType:
            assert False, "Data type must be set for " + perInstanceMemory.ShortName
        elif dataType.ElementType == "IApplicationPrimitiveDataType":
            SetApplicationPrimitiveValueSpecification(constantSpec, initValue, constantSpecCategory, constantSpecUnit)
        elif dataType.ElementType == "IApplicationArrayDataType":
            SetApplicationArrayValueSpecification(constantSpec, initValue, constantSpecCategory, constantSpecUnit)
        elif dataType.ElementType == "IApplicationRecordDataType":
            SetApplicationRecordValueSpecification(constantSpec, dataType, initValue, constantSpecCategory, constantSpecUnit)
        else:
            assert False, "Unsupported data type for NonqueuedReceiverComSpec."
    elif initValue.ElementType == "IConstantSpecification":
        # Use the existent ConstantSpecification.
        constantSpec = initValue
        constantReference = perInstanceMemory.SetNewInitValueConstantReference()
        constantReference.ConstantRef = constantSpec
    else:
        assert False, "Unsupported type of initValue. Must be numerical."
    return constantSpec


def SetQueuedReceiverComSpec(port, dataElement, queueLength=None):
    """
    Creates a QueuedReceiverComSpec and sets the Queuelength for the given data element.
    """
    queuedReceiverComSpec = port.RequiredComSpecs.AddNewQueuedReceiverComSpec()
    queuedReceiverComSpec.DataElementRef = dataElement
    queuedReceiverComSpec.HandleOutOfRange = SdEnums.HandleOutOfRangeEnum.NONE
    queuedReceiverComSpec.SetNewUsesEndToEndProtection()
    queuedReceiverComSpec.UsesEndToEndProtection.SetValue(False)
    if queueLength != None:
        queuedReceiverComSpec.QueueLength = queueLength

def SetSpecialDataRunnableKind(runnable, runnableKind):
    """
    Creates a special data item for the RunnableKind. Valid values are
    {InitRunnable, "TerminateRunnable")
    E.g. SetSpecialDataRunnableKind(runFuelsysSensorsInit, "InitRunnable")
    """
    # Get the AdminData element.
    if runnable.AdminData == None:
        adminData = runnable.SetNewAdminData()
    else:
        adminData = runnable.AdminData

    # Get existing SDG or create a new  SDG.
    sdg = None
    sdgGid = "edve:RunnableKind"
    for sdgItem in adminData.Sdgs.Elements:
        if sdgItem.Gid == sdgGid:
            sdg = sdgItem
            break
    if sdg == None:
        sdg = adminData.Sdgs.AddNew()
        sdg.Gid = sdgGid

    # Set the new value.
    sdgContents = sdg.SetNewSdgContents()
    sd = sdgContents.Sd.AddNew()
    sd.Value = runnableKind

    ##  <ADMIN-DATA>
    ##    <SDGS>
    ##      <SDG GID="edve:RunnableKind">
    ##        <SD xml:space="preserve">InitRunnable</SD>
    ##      </SDG>
    ##    </SDGS>
    ##   </ADMIN-DATA>

def SetSpecialDataFileUri(element, gid, value):
    """
    Sets the value of a custom file attribute for an element. Looks for a
    custom file attribute with the given gid and sets it's value if it exists.
    Otherwise a new special data item with the given value is created.
    """
    # Get the AdminData element.
    if element.AdminData == None:
        adminData = element.SetNewAdminData()
    else:
        adminData = element.AdminData

    # Get existing SDG or create a new  SDG.
    sdg = None
    sdgGid = "edve:taggedFileUri"
    for sdgItem in adminData.Sdgs.Elements:
        if sdgItem.Gid == sdgGid:
            sdg = sdgItem
            break
    if sdg == None:
        sdg = adminData.Sdgs.AddNew()
        sdg.Gid = sdgGid

    # Get existing SD with given GID or create a new  SD.
    sd = None
    if sdg.SdgContents == None:
        sdgContents = sdg.SetNewSdgContents()
    else:
        sdgContents = sdg.SdgContents
    for sdItem in sdgContents.Sd.Elements:
        if sdItem.Gid == gid:
            sd = sdItem
            break
    if sd == None:
        sd = sdgContents.Sd.AddNew()
        sd.Gid = gid

    # Set the new value.
    sd.Value = value

    ##  <ADMIN-DATA>
    ##    <SDGS>
    ##      <SDG GID="edve:taggedFileUri">
    ##        <SD GID="MyFile.c" xml:space="preserve">D:\MyProj\MyFile.c</SD>
    ##      </SDG>
    ##    </SDGS>
    ##   </ADMIN-DATA>


def SetSpecialDataString(element, gid, value):
    """
    Sets the value of a custom string attribute for an element. Looks for a
    custom string attribute with the given gid and sets it's value if it exists.
    Otherwise a new special data item with the given value is created.
    """
    # Get the AdminData element.
    if element.AdminData == None:
        adminData = element.SetNewAdminData()
    else:
        adminData = element.AdminData

    # Get existing SDG or create a new  SDG.
    sdg = None
    sdgGid = "edve:taggedStringValue"
    for sdgItem in adminData.Sdgs.Elements:
        if sdgItem.Gid == sdgGid:
            sdg = sdgItem
            break
    if sdg == None:
        sdg = adminData.Sdgs.AddNew()
        sdg.Gid = sdgGid

    # Get existing SD with given GID or create a new  SD.
    sd = None
    if sdg.SdgContents == None:
        sdgContents = sdg.SetNewSdgContents()
    else:
        sdgContents = sdg.SdgContents
    for sdItem in sdgContents.Sd.Elements:
        if sdItem.Gid == gid:
            sd = sdItem
            break
    if sd == None:
        sd = sdgContents.Sd.AddNew()
        sd.Gid = gid

    # Set the new value.
    sd.Value = value

    ##  <ADMIN-DATA>
    ##    <SDGS>
    ##      <SDG GID="edve:taggedStringValue">
    ##        <SD GID="NoRestartCode" xml:space="preserve">false</SD>
    ##      </SDG>
    ##    </SDGS>
    ##   </ADMIN-DATA>


def SetSwAddrMethod(arElement, swAddrMethod):
    """
    Sets the SwAddrMethod for a VariableDataPrototype or ParameterDataPrototype.
    """
    if arElement.ElementType == "IRunnableEntity":
        arElement.SwAddrMethodRef = swAddrMethod
    else:
        swDataDefProps = arElement.GetOrCreateSwDataDefProps()
        swDataDefProps.SwAddrMethodRef = swAddrMethod


def SetSwCalibrationAccess(arElement, calAccess, displayFormat=None):
    """
    Sets the calibration access method (e.g. SdEnums.SwCalibrationAccessEnum.ReadWrite).
    """
    arElement.ShortName
    swDataDefProps = arElement.GetOrCreateSwDataDefProps()
    swDataDefProps.SwCalibrationAccess = calAccess
    if displayFormat != None:
        swDataDefProps.DisplayFormat = displayFormat


def SetSwValueBlockSize(arElement, valBlkSize):
    """
    Sets the SwValueBlockSize for an element of Category VAL_BLK or ARRAY.
    """
    AssertIf((arElement.Category != "VAL_BLK") and (arElement.Category != "ARRAY"), \
        "Category must be VAL_BLK or ARRAY.")
    swDataDefProps = arElement.GetOrCreateSwDataDefProps()
    swValueBlockSize = swDataDefProps.SetNewSwValueBlockSize()
    swValueBlockSize.MixedContent.AddStringContent(str(valBlkSize))


def SetSwImplPolicy(arElement, swImplPolicy):
    """
    Sets the SwImplPolicy for a VariableDataPrototype.
    Possible values are:
        SystemDeskEnums.SwImplPolicyEnum.{Standard, Queued, MeasurementPoint, Const, Fixed, Undefined}
    """
    swDataDefProps = arElement.GetOrCreateSwDataDefProps()
    swDataDefProps.SwImplPolicy = swImplPolicy


def SetTextTableCompuMethod(compuMethod, textTable, defaultValue=None):
    """
    Configures a CompuMethod for a TEXTTABLE. The parameter textTable must
    be an array of tuples, where each tuple represents one row of the TEXTTABLE, e.g.
        textTable = [
            (0, 0, "off"),
            (1, 1, "on")
        ]
    """
    compuMethod.Category = 'TEXTTABLE'
    compuMethod.DisplayFormat = r"%g"
    compuMethod.UnitRef = GetNoUnit()
    compuInternalToPhys = compuMethod.SetNewCompuInternalToPhys()
    for row in textTable:
        lowerLimit = row[0]
        upperLimit = row[1]
        symbol = row[2]
        compuScale = compuInternalToPhys.CompuScales.AddNew()
        compuScale.ShortLabel = symbol
        compuScaleLL = compuScale.SetNewLowerLimit()
        compuScaleLL.MixedContent.AddStringContent(str(lowerLimit))
        compuScaleLL.IntervalType = SdEnums.IntervalTypeEnum.Closed
        compuScaleUL = compuScale.SetNewUpperLimit()
        compuScaleUL.MixedContent.AddStringContent(str(upperLimit))
        compuScaleUL.IntervalType = SdEnums.IntervalTypeEnum.Closed
        compuScale.ShortLabel = symbol
        compuConst = compuScale.SetNewCompuConst()
        compuConst.Vt = symbol
    if defaultValue != None:
        compuInternalToPhys.CompuDefaultValue.Vt = defaultValue


def StartBswGeneration(ecuConfiguration, command):
    """
    Invokes a BSW generation command in batch mode for the given ECU configuration.
    """
    messages = None
    #
    try:
        oldBatchMode = SdApplication.BatchMode
        SdApplication.BatchMode = True
        messages = ecuConfiguration.StartBswGeneration(command)
        SdApplication.BatchMode = oldBatchMode
    except Exception:
        SdApplication.BatchMode = False
    # Check for messages with severity 'error'.
    ThrowIfError(messages, command)


def TriggerOsTask(osTask, osTaskPeriod):
    """
    Checks if an OsTask is triggered by a periodic alarm. If not, a cyclic OsAlarm
    is created and connected to the HARDWARE counter (SystemTimer).
    """
    osConfiguration = osTask.Parent
    osEnums = __import__(osConfiguration.PythonEnumerationFile)

    # Early return if the task is already triggered by an alarm.
    for osAlarmItem in osConfiguration.OsAlarms.Elements:
        if osAlarmItem.OsAlarmAction.ShortName == "OsAlarmActivateTask":
            if osAlarmItem.OsAlarmAction.OsAlarmActivateTaskRef.ShortName == osTask.ShortName:
                return

    # Find a counter which is connected to a hardware timer
    systemTimer = None
    for osCounter in osConfiguration.OsCounters.Elements:
        if osCounter.OsCounterType == osEnums.OsCounterType.HARDWARE:
            systemTimer = osCounter
            break
    AssertIf(systemTimer == None, "Cannot determine system timer. OS configuration does not contain an OsCounter of type HARDWARE.")
    AssertIf(systemTimer.OsSecondsPerTick <= 0.0, "OsSecondsPerTick must be greater than zero for HARDWARE counter " + systemTimer.ShortName)
    osAlarmCycleTime = round(osTaskPeriod / systemTimer.OsSecondsPerTick)
    AssertIf(abs(osAlarmCycleTime - osTaskPeriod / systemTimer.OsSecondsPerTick) >= 0.001, \
        "Period of task " + osTask.ShortName + " must be an integer multiple of seconds-per-tick for counter " + systemTimer.ShortName)

    # Create a new alarm for the task.
    osAlarm = osConfiguration.OsAlarms.Add("Alarm" + osTask.ShortName)
    osAlarm.OsAlarmCounterRef = systemTimer
    osAlarm.AddOsAlarmAutostart()
    osAlarm.OsAlarmAutostart.OsAlarmAppModeRefs.Add(osConfiguration.OsAppModes.Elements[0])
    osAlarm.OsAlarmAutostart.OsAlarmAutostartType = osEnums.OsAlarmAutostartType.ABSOLUTE
    osAlarm.OsAlarmAutostart.OsAlarmAlarmTime = 0
    osAlarm.OsAlarmAutostart.OsAlarmCycleTime = osAlarmCycleTime
    osAlarmActivateTask = osAlarm.AddOsAlarmActionOsAlarmActivateTask()
    osAlarmActivateTask.OsAlarmActivateTaskRef = osTask


def UpdateBswEventToTaskMapping(rteConfiguration, osTask, \
    bswEventName, removeOldTask=False, positionInTask=None):
    """
    Adds a BswEventToTaskMapping for the given BSW event to the RTE configuration.
    """
    bswEvent = None
    osConfiguration = osTask.Parent

    # Check if an old BswEventToTaskMapping exists.
    bswEventToTaskMapping = None
    for bswModuleInstance in rteConfiguration.RteBswModuleInstances.Elements:
        bswEventToTaskMapping = bswModuleInstance.RteBswEventToTaskMappings.Item(bswEventName)
        if bswEventToTaskMapping:
            break
    AssertIf(bswEventToTaskMapping == None, "No RteBswEventToTaskMapping found for " + bswEventName)
    bswEvent = bswEventToTaskMapping.RteBswEventRef

    # Remove the old task where the BswEvent was executed.
    if removeOldTask:
        if bswEventToTaskMapping.RteBswMappedToTaskRef:
            osTaskOld = osConfiguration.OsTasks.Item(bswEventToTaskMapping.RteBswMappedToTaskRef.ShortName)
            if osTaskOld:
                for osAlarm in osConfiguration.OsAlarms.Elements:
                    try:
                        osAlarmActivateTask = osAlarm.OsAlarmAction
                        if osAlarmActivateTask.OsAlarmActivateTaskRef.ShortName == osTaskOld.ShortName:
                            osAlarm.Delete()
                    except Exception:
                        pass
                osTaskOld.Delete()

    # Determine the next free position in the new OsTask.
    if not positionInTask:
        positionInTask = FindNextPositionInTask(rteConfiguration, osTask)

    # Set the properties of the SchM main function mapping.
    bswEventToTaskMapping.RteBswEventRef = bswEvent
    bswEventToTaskMapping.RteBswMappedToTaskRef = osTask
    bswEventToTaskMapping.RteBswPositionInTask = positionInTask


def UpdateRteEventMapping(ecuConfiguration, osTask, componentName, rteEventName, \
    osEvent=None, osAlarm=None, positionInTask=None, removeOldTask=False):
    """
    Updates a RunnableEntityMapping for the given RTE event to the RTE configuration.
    """
    rteConfiguration = FindModuleConfiguration(ecuConfiguration, "Rte")

    # Get the component prototype and the RTE event.
    ecuFlatView = ecuConfiguration.EcuExtractSystem.RootSwCompositionPrototype
    rootSwComposition = ecuFlatView.SoftwareCompositionTref
    component = rootSwComposition.Components.Item(componentName)
    rteEvent = component.TypeTRef.InternalBehaviors.Elements[0].Events.Item(rteEventName)

    # Determine the next free PositionInTask.
    if not positionInTask:
        positionInTask = FindNextPositionInTask(rteConfiguration, osTask)

    # Find the SwComponentInstance in the RTE configuration.
    swcInstance = rteConfiguration.RteSwComponentInstances.Item(componentName)

    # Get the existing runnable entity mapping.
    runnableEntityMapping = swcInstance.RteEventToTaskMappings.Item(rteEventName)

    # Remove old OsTask, if it exists.
    if removeOldTask:
        if runnableEntityMapping.RteMappedToTaskRef:
            runnableEntityMapping.RteMappedToTaskRef.Delete()

    # Set the new properties.
    runnableEntityMapping.RteMappedToTaskRef = osTask
    runnableEntityMapping.RteEventRef = rteEvent
    runnableEntityMapping.RtePositionInTask = positionInTask
    if osEvent:
        runnableEntityMapping.RteUsedOsEventRef = osEvent
    if osAlarm:
        runnableEntityMapping.RteUsedOsAlarmRef = osAlarm


#---------------------------------------------
# Methods for handling components in diagrams.
#---------------------------------------------

def SetPosition(item, x, y):
    """
    Set the (x,y)-position of an item.
    """
    item.Position.SetCoordinates(x, y)


def SetRelativeLeftSidePosition(item, x):
    """
    Set the relative left side position of an assembly port within a component.
    """
    item.PushToLeftSide()
    item.RelativePosition = x

def SetRelativeRightSidePosition(item, x):
    """
    Set the relative right side position of an assembly port within a component.
    """
    item.PushToRightSide()
    item.RelativePosition = x


def SetSize(item, width, height):
    """
    Set the width and height of an item.
    """
    item.Size.Width = width
    item.Size.Height = height


def SetPositionAndSize(item, x, y, width, height):
    """
    Set the (x,y)-position and width/height of an item.
    """
    SetPosition(item, x, y)
    SetSize(item, width, height)


def SetFillColor(item, fillColor):
    """
    Set the fill color (background color) of an item. Possible colors:
        "orange"
        "lightblue"
        "darkblue"
    """
    if fillColor.lower() == 'orange':
        r = 255
        g = 200
        b = 145
    elif fillColor.lower() == 'lightblue':
        r = 220
        g = 230
        b = 250
    elif fillColor.lower() == 'darkblue':
        r = 0
        g = 0
        b = 255
    elif fillColor.lower() == 'lightgreen':
        r = 0
        g = 250
        b = 0
    else:
        assert 0, "Invalid color name '%s'"  % (fillColor)

    item.FillColor.Set(r, g, b)


def SetTextColor(item, textColor):
    """
    Set the text color of an item. Possible colors:
        "orange"
        "lightblue"
        "darkblue"
    """
    if textColor.lower() == 'orange':
        r = 255
        g = 200
        b = 145
    elif textColor.lower() == 'lightblue':
        r = 220
        g = 230
        b = 250
    elif textColor.lower() == 'darkblue':
        r = 0
        g = 0
        b = 255
    elif textColor.lower() == 'lightgreen':
        r = 0
        g = 250
        b = 0
    else:
        assert 0, "Invalid color name '%s'"  % (textColor)

    item.TextColor.Set(r, g, b)


#----------------
# Simple helpers.
#----------------

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
    elif str(obj.__class__).__contains__("'list'") and bool(obj):
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
    return str1[0:1].upper() + str1[1:len(str)].lower()


#------------
# Assertions.
#------------

def ThrowIfError(messages, command="Command"):
    """
    Checks if a message list returned by a SystemDesk command contains any errors.
    If yes, the first error message is displayed and an exception is thrown.
    """
    if not messages:
        msg = "*** UNEXPECTED RESULT: Command '%s' does not return a message object." % command
        if os.path.exists("__ENABLE_DEBUG__"):
            raise Exception(msg)
        else:
            print(msg)
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

def AssertEmpty(collection, collectionName):
    """
    Throws an assertion if the collection is empty.
    """
    if not collection:
        assert 0, "The %s collection is not defined (NoneType)." % collectionName
    if collection.Count == 0:
        assert 0, "The %s collection at %s must not be empty. The number of elements is %d" \
                  % (collectionName, collection.Parent.ShortName, collection.Count)

def AssertOneElement(collection, collectionName):
    """
    Throws an assertion if the collection does not contain exactly one element.
    """
    if not collection:
        assert 0, "The %s collection is not defined (NoneType)." % collectionName
    if collection.Count != 1:
        assert 0, "The %s collection at %s must contain exactly one element. The number of elements is %d" \
                  % (collectionName, collection.Parent.ShortName, collection.Count)

def AssertZeroOrOneElement(collection, collectionName):
    """
    Throws an assertion if the collection contains more than one element.
    """
    if not collection:
        assert 0, "The %s collection is not defined (NoneType)." % collectionName
    if collection.Count > 1:
        assert 0, "The %s collection at %s must contain zero or one elements. The number of elements is %d" \
                  % (collectionName, collection.Parent.ShortName, collection.Count)


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
        self._StartTime = time.process_time()
        self._LastTime = self._StartTime
        self._CurrentTime = self._StartTime

    def DeltaTime(self, display=True):
        """
        Returns the time since the last call of DeltaTime() or __init__().
        """
        self._CurrentTime = time.process_time()
        deltaTime = self._CurrentTime - self._LastTime
        self._LastTime = self._CurrentTime
        if display:
            PrintD("DeltaTime =%6.3f sec" % deltaTime)
        return deltaTime

    def TotalTime(self, display=True):
        """
        Returns the time since the last call of Start() or __init__().
        """
        self._CurrentTime = time.process_time()
        totalTime = self._CurrentTime - self._StartTime
        if display:
            PrintD("TotalTime =%6.3f sec" % totalTime)
        return totalTime

# Create a global instance of the MiniProfiler.
MiniProfiler = _MiniProfiler()
