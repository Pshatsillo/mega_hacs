from enum import Enum


class Type(Enum):
    NC = 255
    IN = 0
    OUT = 1
    DSEN = 3
    I2C = 4

class Mode(Enum):
    SW = 0
    PWM = 1
    SW_LINK = 3
    DS2413 = 2
    WS281X = 4

class ModeI2C(Enum):
    NC = 0
    SDA = 1
    SCL = 2

class DevI2C(Enum):
    NC = 0
    MCP230XX = 20
    PCA9685 = 21

class Dev(Enum):
    NC = 0
    DHT11 = 1
    DHT22 = 2
    ONEWIRE = 3