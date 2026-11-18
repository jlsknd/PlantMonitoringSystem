"""Development direction 1: ML anomaly detection. Names and operations follow UML."""
from abc import ABC, abstractmethod

class Anomaly:
    def __init__(self, anomalyId, fieldId, sensorId, severity, readingRef, rawType, anomalyScore, detectedAt):
        self.anomalyId=anomalyId; self.fieldId=fieldId; self.sensorId=sensorId; self.severity=severity
        self.readingRef=readingRef; self.rawType=rawType; self.anomalyScore=anomalyScore; self.detectedAt=detectedAt

class AnomalyCause:
    def __init__(self, causeId, causeType, confidence, classifiedAt, anomalyId):
        self.causeId=causeId; self.causeType=causeType; self.confidence=confidence; self.classifiedAt=classifiedAt; self.anomalyId=anomalyId

class MIModel(ABC):
    def __init__(self, modelId, algorithmType, accuracy, version, trainingDate, featureVectorSize):
        self.modelId=modelId; self.algorithmType=algorithmType; self.accuracy=accuracy; self.version=version
        self.trainingDate=trainingDate; self.featureVectorSize=featureVectorSize
    def train(self, data): raise NotImplementedError
    def predict(self, features): raise NotImplementedError
    def evaluate(self, validation): raise NotImplementedError

class RandomForestModel(MIModel):
    def __init__(self, *args, nTrees): super().__init__(*args); self.nTrees=nTrees
    def predict(self, features): raise NotImplementedError

class GradientBoostingModel(MIModel):
    def __init__(self, *args, learningRate, nEstimators): super().__init__(*args); self.learningRate=learningRate; self.nEstimators=nEstimators
    def predict(self, features): raise NotImplementedError

class NeuralNetworkModel(MIModel):
    def __init__(self, *args, layers, dropout): super().__init__(*args); self.layers=layers; self.dropout=dropout
    def predict(self, features): raise NotImplementedError

class AnomalyCauseRepository:
    def getCausesForAnomaly(self, anomalyId): raise NotImplementedError
    def saveCause(self, cause): raise NotImplementedError
    def getTopCauses(self, fieldId, period): raise NotImplementedError

class MIModelRepository:
    def getModel(self, metric): raise NotImplementedError
    def saveModel(self, model): raise NotImplementedError
    def getBestModel(self, metric): raise NotImplementedError
    def deleteModel(self, metric): raise NotImplementedError

class AnomalyDetectionStrategy(ABC):
    @abstractmethod
    def detect(self, readings, indices): raise NotImplementedError

class ThresholdAnomalyStrategy(AnomalyDetectionStrategy):
    def __init__(self, upperBound, lowerBound): self.upperBound=upperBound; self.lowerBound=lowerBound
    def detect(self, readings, indices): raise NotImplementedError

class MIAnomalyStrategy(AnomalyDetectionStrategy):
    def __init__(self, model, minConfidence): self.model=model; self.minConfidence=minConfidence
    def detect(self, readings, indices): raise NotImplementedError

class FalsePositiveFilter:
    def __init__(self, minConsecutiveReadings, minConfidence):
        self.minConsecutiveReadings=minConsecutiveReadings; self.minConfidence=minConfidence
    def filterAnomalies(self, anomalies): raise NotImplementedError
    def requireConsecutiveReadings(self, anomalies, minConsecutive): raise NotImplementedError
    def crossCheckWithCauseAnalysis(self, anomalies, causes): raise NotImplementedError
    def applyConfidenceThreshold(self, anomalies, minConfidence): raise NotImplementedError

class CauseClassifier:
    def __init__(self, model): self.model=model
    def classify(self, anomaly): raise NotImplementedError
    def classifyBatch(self, anomalies): raise NotImplementedError

class MIAnomalyController:
    def __init__(self, strategy, falsePositiveFilter, causeClassifier, modelRepository, causeRepository, problemAreaRepository):
        self.strategy=strategy; self.falsePositiveFilter=falsePositiveFilter; self.causeClassifier=causeClassifier
        self.modelRepository=modelRepository; self.causeRepository=causeRepository; self.problemAreaRepository=problemAreaRepository
    def runDetection(self, fieldId, readings): raise NotImplementedError
    def classifyCauses(self, anomalies): raise NotImplementedError
    def reduceFalsePositives(self, anomalies): raise NotImplementedError
    def retrainModel(self, metric, data): raise NotImplementedError
    def getAnomalyMetrics(self, fieldId, period): raise NotImplementedError
    def switchStrategy(self, strategyType): raise NotImplementedError

class MIAnalyticsView:
    def showAnomalyScores(self, anomalies): raise NotImplementedError
    def showCauseBreakdown(self, causes): raise NotImplementedError
    def showModelMetrics(self, metrics): raise NotImplementedError
    def showFalsePositives(self, filtered): raise NotImplementedError
    def showDetectionMode(self, mode): raise NotImplementedError
    def toggleDetectionMode(self, mode): raise NotImplementedError
