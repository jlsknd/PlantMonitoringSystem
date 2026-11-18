"""Data classes matching the attributes and inheritance in the UML model."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: str
    name: str
    email: str
    password: str


class Agronomist(User):
    pass


class CropScout(User):
    pass


class Analyst(User):
    pass


class GovernmentAgency(User):
    pass


class Engineer(User):
    pass


@dataclass
class Field:
    id: str
    coordinates: str


@dataclass
class Sensor:
    id: str
    type: str
    coordinates: str
    status: str
    fieldId: str


@dataclass
class SensorReading:
    id: str
    type: str
    value: float
    readingTime: datetime
    sensorId: str


@dataclass
class ProblemArea:
    id: str
    problemType: str
    coordinates: str
    status: str
    fieldId: str


@dataclass
class FieldInspection:
    id: str
    timestamp: datetime
    coordinates: str
    description: str
    photoReport: list[str]
    fieldId: str
    inspectorId: str
    problemAreaId: str


@dataclass
class Task:
    id: str
    taskType: str
    status: str
    deadline: datetime
    agronomistId: str
    problemAreaId: str


@dataclass
class Report:
    id: str
    period: str
    content: str
    authorId: str
    fieldIds: list[str]
