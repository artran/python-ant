# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################
# pylint: disable=missing-docstring,invalid-name

import struct

from ant.core import constants
from ant.core.constants import MESSAGE_TX_SYNC
from ant.core.exceptions import MessageError


class MessageType(type):
    
    def __init__(cls, name, bases, dict_):
        super(MessageType, cls).__init__(name, bases, dict_)
        type_ = cls.type
        if type_ is not None:
            cls.TYPES[type_] = cls


class Message(object):
    __metaclass__ = MessageType
    TYPES = {}
    type = None
    
    INCOMPLETE = 'incomplete'
    CORRUPTED = 'corrupted'
    MALFORMED = 'malformed'
    
    def __init__(self, type_=None, payload=None):
        if self.type is None:
            if type_ is not None:
                if (type_ > 0xFF) or (type_ < 0x00):
                    raise MessageError('Could not set type (type out of range).',
                                       internal=Message.CORRUPTED)
                self.type = type_
            else:
                raise RuntimeError('Message cannot be untyped')
        
        self._payload = None
        self.payload = payload if payload is not None else bytearray()
    
    @property
    def payload(self):
        return self._payload
    @payload.setter
    def payload(self, payload):
        if len(payload) > 9:
            raise MessageError('Could not set payload (payload too long).',
                               internal=Message.MALFORMED)
        self._payload = payload
    
    @property
    def checksum(self):
        checksum = MESSAGE_TX_SYNC
        checksum ^= len(self._payload)
        checksum ^= self.type
        for byte in self._payload:
            checksum ^= byte
        return checksum
    
    def encode(self):
        raw = bytearray(( MESSAGE_TX_SYNC, len(self._payload), self.type ))
        raw += self._payload
        raw.append(self.checksum)
        return raw
    
    @classmethod
    def decode(cls, raw):
        raw = bytearray(raw)
        if len(raw) < 5:
            raise MessageError('Could not decode (message is incomplete).',
                               internal=Message.INCOMPLETE)
        
        sync, length, type_ = raw[:3]
        
        if sync != MESSAGE_TX_SYNC:
            raise MessageError('Could not decode (expected TX sync).',
                               internal=Message.CORRUPTED)
        if len(raw) < (length + 4):
            raise MessageError('Could not decode (message is incomplete).',
                               internal=Message.INCOMPLETE)
            
        try:
            msg = cls.TYPES[type_]()
        except KeyError:
            raise MessageError('Could not decode (type "%d" unknown).' % type_)
        msg.payload = raw[3:length + 3]
        
        if msg.checksum != raw[length + 3]:
            raise MessageError('Could not decode (bad checksum).',
                               internal=Message.CORRUPTED)
        
        return msg
    
    def __len__(self):
        return len(self._payload) + 4


class ChannelMessage(Message):
    def __init__(self, type_=None, payload='', number=0x00):
        super(ChannelMessage, self).__init__(type_, bytearray(1) + payload)
        self.channelNumber = number
    
    @property
    def channelNumber(self):
        return self._payload[0]
    @channelNumber.setter
    def channelNumber(self, number):
        if (number > 0xFF) or (number < 0x00):
            raise MessageError('Could not set channel number (out of range).')
        
        self._payload[0] = number


# Config messages
class ChannelUnassignMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_UNASSIGN
    
    def __init__(self, number=0x00):
        super(ChannelUnassignMessage, self).__init__(number=number)


class ChannelAssignMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_ASSIGN
    
    def __init__(self, number=0x00, type_=0x00, network=0x00):
        super(ChannelAssignMessage, self).__init__(payload=bytearray(2), number=number)
        self.channelType = type_
        self.networkNumber = network
    
    @property
    def channelType(self):
        return self._payload[1]
    @channelType.setter
    def channelType(self, type_):
        self._payload[1] = type_
    
    @property
    def networkNumber(self):
        return self._payload[2]
    @networkNumber.setter
    def networkNumber(self, number):
        self._payload[2] = number


class ChannelIDMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_ID
    
    def __init__(self, number=0x00, device_number=0x0000, device_type=0x00,
                 trans_type=0x00):
        super(ChannelIDMessage, self).__init__(payload=bytearray(4), number=number)
        self.deviceNumber = device_number
        self.deviceType = device_type
        self.transmissionType = trans_type
    
    @property
    def deviceNumber(self):
        return struct.unpack('<H', str(self._payload[1:3]))[0]
    @deviceNumber.setter
    def deviceNumber(self, device_number):
        self._payload[1:3] = struct.pack('<H', device_number)
    
    @property
    def deviceType(self):
        return self._payload[3]
    @deviceType.setter
    def deviceType(self, device_type):
        self._payload[3] = device_type
    
    @property
    def transmissionType(self):
        return self._payload[4]
    @transmissionType.setter
    def transmissionType(self, trans_type):
        self._payload[4] = trans_type


class ChannelPeriodMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_PERIOD
    
    def __init__(self, number=0x00, period=8192):
        super(ChannelPeriodMessage, self).__init__(payload=bytearray(2), number=number)
        self.channelPeriod = period
    
    @property
    def channelPeriod(self):
        return struct.unpack('<H', str(self._payload[1:3]))[0]
    @channelPeriod.setter
    def channelPeriod(self, period):
        self._payload[1:3] = struct.pack('<H', period)


class ChannelSearchTimeoutMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_SEARCH_TIMEOUT
    
    def __init__(self, number=0x00, timeout=0xFF):
        super(ChannelSearchTimeoutMessage, self).__init__(payload=bytearray(1),
                                                          number=number)
        self.setTimeout(timeout)
    
    def getTimeout(self):
        return self._payload[1]
    
    def setTimeout(self, timeout):
        self._payload[1] = timeout


class ChannelFrequencyMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_FREQUENCY
    
    def __init__(self, number=0x00, frequency=66):
        super(ChannelFrequencyMessage, self).__init__(payload=bytearray(1), number=number)
        self.setFrequency(frequency)
    
    def getFrequency(self):
        return self._payload[1]
    
    def setFrequency(self, frequency):
        self._payload[1] = frequency


class ChannelTXPowerMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_TX_POWER
    
    def __init__(self, number=0x00, power=0x00):
        super(ChannelTXPowerMessage, self).__init__(payload=bytearray(1), number=number)
        self.setPower(power)
    
    def getPower(self):
        return self._payload[1]
    
    def setPower(self, power):
        self._payload[1] = power


class NetworkKeyMessage(Message):
    type = constants.MESSAGE_NETWORK_KEY
    
    def __init__(self, number=0x00, key='\x00' * 8):
        super(NetworkKeyMessage, self).__init__(payload=bytearray(9))
        self.setNumber(number)
        self.setKey(key)
    
    def getNumber(self):
        return self._payload[0]
    
    def setNumber(self, number):
        self._payload[0] = number
    
    def getKey(self):
        return self._payload[1:]
    
    def setKey(self, key):
        self._payload[1:] = key


class TXPowerMessage(Message):
    type = constants.MESSAGE_TX_POWER
    
    def __init__(self, power=0x00):
        super(TXPowerMessage, self).__init__(payload=bytearray(2))
        self.setPower(power)
    
    def getPower(self):
        return self._payload[1]
    
    def setPower(self, power):
        self._payload[1] = power


# Control messages
class SystemResetMessage(Message):
    type = constants.MESSAGE_SYSTEM_RESET
    
    def __init__(self):
        super(SystemResetMessage, self).__init__(payload=bytearray(1))


class ChannelOpenMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_OPEN
    
    def __init__(self, number=0x00):
        super(ChannelOpenMessage, self).__init__(number=number)


class ChannelCloseMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_CLOSE
    
    def __init__(self, number=0x00):
        super(ChannelCloseMessage, self).__init__(number=number)


class ChannelRequestMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_REQUEST
    
    def __init__(self, number=0x00, message_id=constants.MESSAGE_CHANNEL_STATUS):
        super(ChannelRequestMessage, self).__init__(payload=bytearray(1), number=number)
        self.setMessageID(message_id)
    
    def getMessageID(self):
        return self._payload[1]
    
    def setMessageID(self, message_id):
        if (message_id > 0xFF) or (message_id < 0x00):
            raise MessageError('Could not set message ID (out of range).')
        
        self._payload[1] = message_id


class RequestMessage(ChannelRequestMessage):
    pass


# Data messages
class ChannelBroadcastDataMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_BROADCAST_DATA
    
    def __init__(self, number=0x00, data='\x00' * 7):
        super(ChannelBroadcastDataMessage, self).__init__(payload=data, number=number)


class ChannelAcknowledgedDataMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_ACKNOWLEDGED_DATA
    
    def __init__(self, number=0x00, data='\x00' * 7):
        super(ChannelAcknowledgedDataMessage, self).__init__(payload=data, number=number)


class ChannelBurstDataMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_BURST_DATA
    
    def __init__(self, number=0x00, data='\x00' * 7):
        super(ChannelBurstDataMessage, self).__init__(payload=data, number=number)


# Channel event messages
class ChannelEventMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_EVENT
    
    def __init__(self, number=0x00, message_id=0x00, message_code=0x00):
        super(ChannelEventMessage, self).__init__(payload=bytearray(2), number=number)
        self.setMessageID(message_id)
        self.setMessageCode(message_code)
    
    def getMessageID(self):
        return self._payload[1]
    
    def setMessageID(self, message_id):
        if (message_id > 0xFF) or (message_id < 0x00):
            raise MessageError('Could not set message ID (out of range).')
        
        self._payload[1] = message_id
    
    def getMessageCode(self):
        return self._payload[2]
    
    def setMessageCode(self, message_code):
        if (message_code > 0xFF) or (message_code < 0x00):
            raise MessageError('Could not set message code (out of range).')
        
        self._payload[2] = message_code


# Requested response messages
class ChannelStatusMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_STATUS
    
    def __init__(self, number=0x00, status=0x00):
        super(ChannelStatusMessage, self).__init__(payload=bytearray(1), number=number)
        self.setStatus(status)
    
    def getStatus(self):
        return self._payload[1]
    
    def setStatus(self, status):
        if (status > 0xFF) or (status < 0x00):
            raise MessageError('Could not set channel status (out of range).')
        
        self._payload[1] = status


class VersionMessage(Message):
    type = constants.MESSAGE_VERSION
    
    def __init__(self, version='\x00' * 9):
        super(VersionMessage, self).__init__(payload=bytearray(9))
        self.setVersion(version)
    
    def getVersion(self):
        return self._payload
    
    def setVersion(self, version):
        if len(version) != 9:
            raise MessageError('Could not set ANT version (expected 9 bytes).')
        
        self.payload = bytearray(version)


class StartupMessage(Message):
    type = constants.MESSAGE_STARTUP
    
    def __init__(self, startupMessage=0x00):
        super(StartupMessage, self).__init__(self, payload=bytearray(1))
        self.setStartupMessage(startupMessage)
        
    def getStartupMessage(self):
        return self._payload[0]
        
    def setStartupMessage(self, startupMessage):
        if (startupMessage > 0xFF) or (startupMessage < 0x00):
            raise MessageError('Could not set start-up message (out of range).')
        self._payload[0] = startupMessage


class CapabilitiesMessage(Message):
    type = constants.MESSAGE_CAPABILITIES
    def __init__(self, max_channels=0x00, max_nets=0x00, std_opts=0x00,
                 adv_opts=0x00, adv_opts2=0x00):
        super(CapabilitiesMessage, self).__init__(payload=bytearray(4))
        self.setMaxChannels(max_channels)
        self.setMaxNetworks(max_nets)
        self.setStdOptions(std_opts)
        self.setAdvOptions(adv_opts)
        if adv_opts2 is not None:
            self.setAdvOptions2(adv_opts2)
    
    def getMaxChannels(self):
        return self._payload[0]
    
    def getMaxNetworks(self):
        return self._payload[1]
    
    def getStdOptions(self):
        return self._payload[2]
    
    def getAdvOptions(self):
        return self._payload[3]
    
    def getAdvOptions2(self):
        return self._payload[4] if len(self._payload) == 5 else 0x00
    
    def setMaxChannels(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set max channels ' \
                                   '(out of range).')
        self._payload[0] = num
    
    def setMaxNetworks(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set max networks (out of range).')
        self._payload[1] = num
    
    def setStdOptions(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set std options (out of range).')
        self._payload[2] = num
    
    def setAdvOptions(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set adv options (out of range).')
        self._payload[3] = num
    
    def setAdvOptions2(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set adv options 2 (out of range).')
        if len(self._payload) == 4:
            self._payload.append('\x00')
        self._payload[4] = num


class SerialNumberMessage(Message):
    type = constants.MESSAGE_SERIAL_NUMBER
    
    def __init__(self, serial='\x00' * 4):
        super(SerialNumberMessage, self).__init__()
        self.setSerialNumber(serial)
    
    def getSerialNumber(self):
        return self._payload
    
    def setSerialNumber(self, serial):
        if len(serial) != 4:
            raise MessageError('Could not set serial number (expected 4 bytes).')
        
        self.payload = bytearray(serial)
