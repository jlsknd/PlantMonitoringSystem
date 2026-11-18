"""Development direction 3: external integration; UML class/operation names."""
class IExternalDataSource:
    def getSourceId(self): raise NotImplementedError
    def getSourceType(self): raise NotImplementedError
    def isAvailable(self): raise NotImplementedError
    def fetchObservations(self, fieldId, period): raise NotImplementedError
    def sync(self): raise NotImplementedError

class ExternalDataSource(IExternalDataSource):
    def __init__(self, sourceId, sourceType, connectionStatus, lastSyncTime):
        self.sourceId=sourceId; self.sourceType=sourceType; self.connectionStatus=connectionStatus; self.lastSyncTime=lastSyncTime
    def connect(self): raise NotImplementedError
    def disconnect(self): raise NotImplementedError
    def sync(self): raise NotImplementedError
    def fetchObservations(self, fieldId, period): raise NotImplementedError
    def getSourceId(self): return self.sourceId
    def getSourceType(self): return self.sourceType
    def isAvailable(self): return self.connectionStatus == "online"

class ExternalObservation:
    def __init__(self, observationId, sourceType, timestamp, value, coordinates, observedAt, sourceId, mediaRef):
        self.observationId=observationId; self.sourceType=sourceType; self.timestamp=timestamp; self.value=value
        self.coordinates=coordinates; self.observedAt=observedAt; self.sourceId=sourceId; self.mediaRef=mediaRef

class IFieldDevice:
    def getDeviceId(self): raise NotImplementedError
    def getDeviceType(self): raise NotImplementedError
    def getStatus(self): raise NotImplementedError
    def getGPSCoordinates(self): raise NotImplementedError
    def receiveTask(self, task): raise NotImplementedError
    def reportStatus(self, telemetry): raise NotImplementedError

class FieldDevice(IFieldDevice):
    def getDeviceId(self): raise NotImplementedError
    def getDeviceType(self): raise NotImplementedError
    def getStatus(self): raise NotImplementedError
    def getGPSCoordinates(self): raise NotImplementedError
    def receiveTask(self, task): raise NotImplementedError
    def reportStatus(self, telemetry): raise NotImplementedError

class Drone(FieldDevice):
    def __init__(self, batteryLevel, maxAltitude): self.batteryLevel=batteryLevel; self.maxAltitude=maxAltitude
    def receiveTask(self, task): raise NotImplementedError
    def reportStatus(self, telemetry): raise NotImplementedError
    def fetchObservations(self, fieldId, period): raise NotImplementedError

class WeatherDataProvider(ExternalDataSource):
    def __init__(self, *args, apiEndpoint, cacheTTL): super().__init__(*args); self.apiEndpoint=apiEndpoint; self.cacheTTL=cacheTTL
    def fetchObservations(self, fieldId, period): raise NotImplementedError

class SatelliteImageSource(ExternalDataSource):
    def __init__(self, *args, orbitalProvider, resolution): super().__init__(*args); self.orbitalProvider=orbitalProvider; self.resolution=resolution
    def fetchObservations(self, fieldId, period): raise NotImplementedError

class IrrigationSystem(FieldDevice):
    def __init__(self, valveCount, flowRate): self.valveCount=valveCount; self.flowRate=flowRate
    def receiveTask(self, task): raise NotImplementedError
    def reportStatus(self, telemetry): raise NotImplementedError

class AgriculturalMachine(FieldDevice):
    def __init__(self, machineType, fuelLevel, gpsTrackerId):
        self.machineType=machineType; self.fuelLevel=fuelLevel; self.gpsTrackerId=gpsTrackerId
    def receiveTask(self, task): raise NotImplementedError
    def reportStatus(self, telemetry): raise NotImplementedError

class DeviceTelemetry:
    def __init__(self, telemetryId, deviceId, timestamp, gpsCoordinates, status, taskId, batteryLevel):
        self.telemetryId=telemetryId; self.deviceId=deviceId; self.timestamp=timestamp; self.gpsCoordinates=gpsCoordinates
        self.status=status; self.taskId=taskId; self.batteryLevel=batteryLevel

class DroneObservation:
    def __init__(self, flightAltitude, cameraMode): self.flightAltitude=flightAltitude; self.cameraMode=cameraMode

class WeatherObservation:
    def __init__(self, temperature, humidity, precipitation, windSpeed):
        self.temperature=temperature; self.humidity=humidity; self.precipitation=precipitation; self.windSpeed=windSpeed

class SatelliteObservation:
    def __init__(self, band, ndviIndex): self.band=band; self.ndviIndex=ndviIndex

class DeviceRegistry:
    def registerDevice(self, device): raise NotImplementedError
    def unregisterDevice(self, deviceId): raise NotImplementedError
    def getDevices(self): raise NotImplementedError
    def getDevicesByType(self, type): raise NotImplementedError
    def getOnlineDevices(self): raise NotImplementedError

class SourceRegistry:
    def registerSource(self, source): raise NotImplementedError
    def unregisterSource(self, sourceId): raise NotImplementedError
    def getSources(self): raise NotImplementedError
    def getSourcesByType(self, type): raise NotImplementedError
    def getAvailableSources(self): raise NotImplementedError

class ExternalObservationRepository:
    def saveObservation(self, observation): raise NotImplementedError
    def getObservations(self, fieldId, period): raise NotImplementedError

class DeviceTelemetryRepository:
    def saveTelemetry(self, telemetry): raise NotImplementedError
    def getByDeviceId(self, deviceId): raise NotImplementedError
    def getLatestByDeviceId(self, deviceId): raise NotImplementedError

class DataFusionService:
    def fuseReadings(self, readings, observations): raise NotImplementedError
    def computeEnrichedHealthIndex(self, fieldId): raise NotImplementedError
    def crossValidate(self, reading, observation): raise NotImplementedError
    def weightBySource(self, sourceType): raise NotImplementedError
    def detectSensorDrift(self, observations): raise NotImplementedError

class TaskExecutionService:
    def assignTask(self, task, device): raise NotImplementedError
    def trackExecution(self, taskId): raise NotImplementedError
    def receiveTelemetry(self, telemetry): raise NotImplementedError
    def handleDeviceStatus(self, telemetry): raise NotImplementedError
    def matchDeviceToTask(self, task): raise NotImplementedError

class IntegrationFacade:
    def refreshExternalData(self, fieldId, period): raise NotImplementedError
    def getDeviceTelemetry(self, deviceId): raise NotImplementedError
    def dispatchTasksToDevices(self, tasks): raise NotImplementedError
    def registerNewDevice(self, device): raise NotImplementedError
    def registerNewSource(self, source): raise NotImplementedError
    def syncSources(self, period, fieldId): raise NotImplementedError

class ExternalIntegrationView:
    def showExternalLayerObservations(self, observations): raise NotImplementedError
    def showDeviceMap(self, devices): raise NotImplementedError
    def showDeviceTelemetry(self, telemetry): raise NotImplementedError
    def showFusionMetrics(self, metrics): raise NotImplementedError
    def triggerRefresh(self, fieldId, period): raise NotImplementedError
    def assignTaskToDevice(self, task, deviceId): raise NotImplementedError

class FactoryIntegrationComponents:
    def createSatelliteSource(self, config): raise NotImplementedError
    def createWeatherProvider(self, config): raise NotImplementedError
    def createDrone(self, config): raise NotImplementedError
    def createIrrigationSystem(self, config): raise NotImplementedError
    def createAgriculturalMachine(self, config): raise NotImplementedError
    def createSourceRegistry(self): raise NotImplementedError
    def createDeviceRegistry(self): raise NotImplementedError
    def createExecutionService(self): raise NotImplementedError
    def createFacade(self, sourceRegistry, deviceRegistry, taskExecutionService, dataFusionService): raise NotImplementedError
    def registerAll(self, container): raise NotImplementedError
