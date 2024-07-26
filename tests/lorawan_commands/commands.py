from enum import IntEnum


COMMAND_MAP = {
    "": {"ascii": "", "at": "", "binary": b"", "args": 0},
    "lorawan": {"ascii": "lorawan", "at": "AT+l", "binary": b"\x9F", "args": 0},
    "stack": {"ascii": "stack", "at": "AT+s", "binary": b"\xA0", "args": 0},
    "ping": {"ascii": "ping", "at": "AT!p", "binary": b"\x11", "args": 0},
    "sevent": {"ascii": "sevent", "at": "AT&E", "binary": b"\x4F", "args": 1},
    "gevent": {"ascii": "gevent", "at": "AT*E", "binary": b"\x4A", "args": 0},
    "sfreqz": {"ascii": "sfreqz", "at": "AT*b", "binary": b"\xD2", "args": 4},
    "crcgen": {"ascii": "crcgen", "at": "AT*s", "binary": b"\xF3", "args": 1},
    "sbandwidth": {"ascii": "sbandwidth", "at": "AT*c", "binary": b"\xD3", "args": 1},
    "scodingrate": {"ascii": "scodingrate", "at": "AT*e", "binary": b"\xD4", "args": 1},
    "spreadfactor": {"ascii": "spreadfactor", "at": "AT*l", "binary": b"\xDB", "args": 1},
    "sendb": {"ascii": "sendb", "at": "AT+X", "binary": b"\x20", "args": 0},
    "geta": {"ascii": "geta", "at": "AT+A", "binary": b"\x23", "args": 0},
    "checkr": {"ascii": "checkr", "at": "AT+r", "binary": b"\x24", "args": 0},
    "sparser": {"ascii": "sparser", "at": "AT!P", "binary": b"\xFB", "args": 0},
    "getx": {"ascii": "getx", "at": "AT+y", "binary": b"\x1E", "args": 0},
    "autorx": {"ascii": "autorx", "at": "AT&R", "binary": b"\x4C", "args": 1},
    "spwr": {"ascii": "spwr", "at": "AT%W", "binary": b"\x41", "args": 1},
    "pwr": {"ascii": "pwr", "at": "AT%w", "binary": b"\x42", "args": 0},
    "rssi": {"ascii": "rssi", "at": "AT%s", "binary": b"\x31", "args": 0},
}


RESPONSE_MAP = {
    "stack": {
        "test": "00",
        "wmbus": "01",
        "lorawan": "02",
        "lora": "03",
        "lorafhss": "04",
        "none": "FF",
    },
    "ping": {
        "PONG!": "",
    },
}


class AutoRxMode(IntEnum):
    OFF = 0x00
    DATA_BIN = 0x01
    DATA_AND_HEADER_BIN = 0x02
    DATA_AND_HEADER_HEX = 0x03


class Bandwidth(IntEnum):
    BW_7_8_KHZ = 0
    BW_10_4_KHZ = 1
    BW_15_6_KHZ = 2
    BW_20_8_KHZ = 3
    BW_31_2_KHZ = 4
    BW_41_6_KHZ = 5
    BW_62_5_KHZ = 6
    BW_125_KHZ = 7
    BW_250_KHZ = 8
    BW_500_KHZ = 9


class CodingRate(IntEnum):
    CODING_RATE_4_TO_5 = 1
    CODING_RATE_4_TO_6 = 2
    CODING_RATE_4_TO_7 = 3
    CODING_RATE_4_TO_8 = 4


class SpreadingFactor(IntEnum):
    SF_5 = 5
    SF_6 = 6
    SF_7 = 7
    SF_8 = 8
    SF_9 = 9
    SF_10 = 10
    SF_11 = 11
    SF_12 = 12


class CmdMeta(type):
    def __init__(cls, *args, **kwargs):
        cls._mode = ""

    @property
    def mode(cls):
        return cls._mode

    @mode.setter
    def mode(cls, value):
        cls._mode = value


class Cmd(metaclass=CmdMeta):
    ascii: str
    at: str
    binary: bytes

    def __init__(self, command, args=(), response="OK00>"):
        self._command = command
        self._args = args
        self._response = response

    def __str__(self):
        parts = [f"command: \"{self._command}\""]
        if self._args:
            parts.append("args: \"" + " ".join([str(a) for a in self._args]) + "\"")
        if self._response:
            parts.append(f"response: \"{self._response}\"")
        return " ".join(parts)

    def command_property(self):
        if self._command is None:
            return
        if Cmd.mode == "ascii":
            # cmd = f"{COMMAND_MAP[self._command]['ascii']}"
            cmd = self.ascii
            for arg in self._args:
                cmd += f" {arg}"
            return cmd
        elif Cmd.mode == "at":
            # cmd = f"{COMMAND_MAP[self._command]['at']}"
            cmd = self.at
            for arg in self._args:
                cmd += f" {arg}"
            return cmd
        elif Cmd.mode == "binary":
            cmd = f"0x1B 0x2A "
            # binary_cmd = COMMAND_MAP[self._command]['binary']
            # cmd += f"0x{int(binary_cmd.hex(), 16):>02X} " if binary_cmd else ""
            if self.binary:
                cmd += f"0x{int(self.binary.hex(), 16):>02X} "
            # if COMMAND_MAP[self._command]["args"] == 1:
            if len(self._args) == 1:
                cmd += f"0x{int(self._args[0]):>02X} "
            cmd += "0x1B 0x42"
            return cmd

        raise ValueError(f"Invalid command mode: {self._mode}")

    @property
    def command(self):
        return self.command_property()

    @property
    def response(self):
        if Cmd.mode == "binary":
            if self._response == "OK00>":
                return "1B 50 1B 51 01"
        return self._response


class CmdRtrn(Cmd):
    def __init__(self, command, return_value, args=()):
        response = "" if Cmd.mode == "binary" else "OK00>"
        super().__init__(command, args, response=response)
        self._return_value = return_value

    def __str__(self):
        parts = [f"command: \"{self._command}\""]
        if self._args:
            parts.append("args: \"" + " ".join([str(a) for a in self._args]) + "\"")
        if self._return_value:
            parts.append(f"return: \"{self._return_value}\"")
        if self._response:
            parts.append(f"response: \"{self._response}\"")
        return " ".join(parts)

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            _return_value_parts = ["1B 50"]
            if self._command in RESPONSE_MAP:
                _return_value_parts.append(RESPONSE_MAP[self._command][self._return_value].strip())
            elif self._return_value:
                _return_value_parts.append(f"{int(self._return_value):>02X}")
            _return_value_parts.append("1B 51 01")
            while "" in _return_value_parts:
                _return_value_parts.remove("")
            return " ".join(_return_value_parts)
        else:
            return self._return_value


class WakeUp(Cmd):
    ascii = ""
    at = ""
    binary = b""

    def __init__(self):
        super().__init__("", response=None)

    def __str__(self):
        return "WakeUp"

class Lorawan(Cmd):
    ascii = " lorawan"
    at = " AT+l"
    binary =  b"\x9D"

    def __init__(self):
        super().__init__("lorawan")
       
class Stack(CmdRtrn):
    ascii = "stack"
    at = "AT+s"
    binary = b"\xA0"

    def __init__(self, stack):
        self.stack = stack
        super().__init__("stack", self.stack)

class Ping(CmdRtrn):
    ascii = "ping"
    at = "AT!p"
    binary = b"\x11"

    def __init__(self,return_value):
        super().__init__("ping", return_value)

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            _return_value_parts = ["1B 50 1B 51 01"]
            return " ".join(_return_value_parts)
        else:
            return self._return_value
        

class Sevent(Cmd):
    ascii = " sevent"  
    at = " AT&E"
    binary =  b"\x4F"

    def __init__(self, enabled):
        self.enabled = enabled
        super().__init__(self.ascii, "1" if self.enabled else "0")

class Sconfirm(Cmd):
    ascii = " sconfirm"
    at = " AT+F"
    binary =  b"\x9C"

    def __init__(self, enabled):
        self.enabled = enabled
        super().__init__("sconfirm", args=("01" if self.enabled else "00",))

class Confirm(CmdRtrn):
    ascii = " confirm"
    at = " AT+f"
    binary =  b"\x9B"

    def __init__(self, enabled):
        self.enabled = enabled
        super().__init__(self.ascii, "01" if self.enabled else "00")

class Devid(CmdRtrn):
    ascii = " devid"
    at = " AT+I"
    binary =  b"\x4E"

    def __init__(self, return_value):
        super().__init__("devid", return_value)  

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            _return_value_parts = ["1B 50", self._return_value, "1B 51 01"]
            return " ".join(_return_value_parts)
        else:
            return self._return_value

class Lwstatus(CmdRtrn):
    ascii = " lwstatus"
    at = " AT+u"
    binary =  b"\xA5"

    def __init__(self, return_value):
        super().__init__("lwstatus", return_value)  

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            _return_value_parts = ["1B 50 01 1B 51 01"]
            return " ".join(_return_value_parts)
        else:
            return self._return_value

#class Gevent(CmdRtrn):
#     ascii = " gevent" 
#     at = " AT*E" 
#     binary =  b"\x4A"

#    def __init__(self, enabled):
#        self.enabled = enabled
#        super().__init__(self.ascii, "01" if self.enabled else "00")

class Sappeui(Cmd):
    ascii = " sAppEUI"
    at = " AT+O"
    binary =  b"\xA7"

    def __init__(self, sappeui):
        self.sappeui = sappeui
        super().__init__("sAppEUI", args=(self.sappeui,))
    
    @property
    def command(self):
        if Cmd.mode == "binary":
            cmd = f"0x1B 0x2A "
            cmd += f"0x{int(self.binary.hex(), 16):>02X} "
            # binary_cmd = COMMAND_MAP[self._command]['binary']
            # cmd += f"0x{int(binary_cmd.hex(), 16):>02X} " if binary_cmd else ""
            _sappeui = (self.sappeui).split()
            cmd += " ".join(f"0x{sappeui}" for sappeui in _sappeui)
            cmd += " 0x1B 0x42"
            return cmd
        return self.command_property()

class Gappeui(CmdRtrn):
    ascii = " gAppEUI"
    at = " AT+e"
    binary =  b"\x63"

    def __init__(self, return_value):
        super().__init__("gAppEUI", return_value)  

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            _return_value_parts = ["1B 50", self._return_value, "1B 51 01"]
            return " ".join(_return_value_parts)
        else:
            return self._return_value

class Sappkey(Cmd):
    ascii = " sAppKey"
    at = " AT+K"
    binary =  b"\xA9"

    def __init__(self, sappkey):
        self.sappkey = sappkey
        super().__init__("sAppKey", args=(self.sappkey,))
    
    @property
    def command(self):
        if Cmd.mode == "binary":
            cmd = f"0x1B 0x2A "
            cmd += f"0x{int(self.binary.hex(), 16):>02X} "
            # binary_cmd = COMMAND_MAP[self._command]['binary']
            # cmd += f"0x{int(binary_cmd.hex(), 16):>02X} " if binary_cmd else ""
            _sappkey = (self.sappkey).split()
            cmd += " ".join(f"0x{sappkey}" for sappkey in _sappkey)
            cmd += " 0x1B 0x42"
            return cmd
        return self.command_property()

class Gappkey(CmdRtrn):
    ascii = " gAppKey"
    at = " AT+q"
    binary =  b"\x64"

    def __init__(self, return_value):
        super().__init__("gAppKey", return_value)

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            _return_value_parts = ["1B 50", self._return_value, "1B 51 01"]
            return " ".join(_return_value_parts)
        else:
            return self._return_value


class Sappskey(Cmd):
    ascii = " sAppSKey"
    at = " AT+k"
    binary =  b"\xAE"

    def __init__(self, sappskey):
        self.sappskey = sappskey
        super().__init__("sAppSKey", args=(self.sappskey,))
    
    @property
    def command(self):
        if Cmd.mode == "binary":
            cmd = f"0x1B 0x2A "
            cmd += f"0x{int(self.binary.hex(), 16):>02X} "
            # binary_cmd = COMMAND_MAP[self._command]['binary']
            # cmd += f"0x{int(binary_cmd.hex(), 16):>02X} " if binary_cmd else ""
            _sappskey = (self.sappskey).split()
            cmd += " ".join(f"0x{sappskey}" for sappskey in _sappskey)
            cmd += " 0x1B 0x42"
            return cmd
        return self.command_property()

class Gappskey(CmdRtrn):
    ascii = " gAppSKey"
    at = " AT+j"
    binary =  b"\x67"

    def __init__(self, return_value):
        super().__init__("gAppSKey", return_value)  

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            _return_value_parts = ["1B 50", self._return_value, "1B 51 01"]
            return " ".join(_return_value_parts)
        else:
            return self._return_value

class Snwkskey(Cmd):
    ascii = " sNwkSKey"
    at = " AT+N"
    binary =  b"\xAD"

    def __init__(self, snwkskey):
        self.snwkskey = snwkskey
        super().__init__("sNwkSKey", args=(self.snwkskey,))
    
    @property
    def command(self):
        if Cmd.mode == "binary":
            cmd = f"0x1B 0x2A "
            cmd += f"0x{int(self.binary.hex(), 16):>02X} "
            # binary_cmd = COMMAND_MAP[self._command]['binary']
            # cmd += f"0x{int(binary_cmd.hex(), 16):>02X} " if binary_cmd else ""
            _snwkskey = (self.snwkskey).split()
            cmd += " ".join(f"0x{snwkskey}" for snwkskey in _snwkskey)
            cmd += " 0x1B 0x42"
            return cmd
        return self.command_property()

class Gnwkskey(CmdRtrn):
    ascii = " gNwkSKey"
    at = " AT+n"
    binary =  b"\x66"

    def __init__(self, return_value):
        super().__init__("gNwkSKey", return_value)

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            _return_value_parts = ["1B 50", self._return_value, "1B 51 01"]
            return " ".join(_return_value_parts)
        else:
            return self._return_value

class Sdevaddr(Cmd):
    ascii = " sDevAddr"
    at = " AT+V"
    binary =  b"\xAC"

    def __init__(self, sdevaddr):
        self.sdevaddr = sdevaddr
        super().__init__("sDevAddr", args=(self.sdevaddr,))
    
    @property
    def command(self):
        if Cmd.mode == "binary":
            cmd = f"0x1B 0x2A "
            cmd += f"0x{int(self.binary.hex(), 16):>02X} "
            # binary_cmd = COMMAND_MAP[self._command]['binary']
            # cmd += f"0x{int(binary_cmd.hex(), 16):>02X} " if binary_cmd else ""
            _sdevaddr = (self.sdevaddr).split()
            cmd += " ".join(f"0x{sdevaddr}" for sdevaddr in _sdevaddr)
            cmd += " 0x1B 0x42"
            return cmd
        return self.command_property()

class Gdevaddr(CmdRtrn):
    ascii = " gDevAddr"
    at = " AT+v"
    binary =  b"\x65"

    def __init__(self, return_value):
        super().__init__("gDevAddr", return_value)

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            _return_value_parts = ["1B 50", self._return_value, "1B 51 01"]
            return " ".join(_return_value_parts)
        else:
            return self._return_value

class Sotaa(Cmd):
    ascii = " sOTAA"
    at = " AT+T"
    binary =  b"\xA8"

    def __init__(self, enabled):
        self.enabled = enabled
        super().__init__("sOTAA", args=("01" if self.enabled else "00",))

class Gotaa(CmdRtrn):
    ascii = " gOTAA"
    at = " AT+t"
    binary =  b"\xAF"
    def __init__(self, enabled):
        self.enabled = enabled
        super().__init__(self.ascii, "01" if self.enabled else "00")

class SendBytes(Cmd):
    ascii = "sendb"
    at = "AT+X"
    binary = b"\x20"

    def __init__(self, length, string: str):
        self.length = length
        self.string = string
        super().__init__("sendb", args=(f"{self.length:02X}",))

    @property
    def command(self):
        if Cmd.mode == "binary":
            cmd = f"0x1B 0x2A "
            # binary_cmd = COMMAND_MAP[self._command]['binary']
            # cmd += f"0x{int(binary_cmd.hex(), 16):>02X} " if binary_cmd else ""
            cmd += f"0x{int(self.binary.hex(), 16):>02X} "
            for char in self.string.encode():
                cmd += f"0x{int(char):>02X} "
            cmd += "0x1B 0x42"
            return cmd
        return self.command_property()

class Lwjoin(Cmd):
    ascii = " lwjoin"
    at = " AT+J"
    binary =  b"\xA6"

    def __init__(self):
        super().__init__("lwjoin")

class Lwjoinbin(CmdRtrn):
    ascii = " lwjoin"
    at = " AT+J"
    binary =  b"\xA6"

    def __init__(self, return_value):
        super().__init__("lwjoin", return_value)

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            self._return_value = "1B 51 01 1B 53 4A 6F 69 6E 69 6E 67 20 74 68 65 20 4C 6F 52 61 57 41 4E 20 6E 65 74 77 6F 72 6B 2E 2E 2E"
            _return_value_parts = ["1B 50", self._return_value, "1B 54"]
            return " ".join(_return_value_parts)
        else:
            return self._return_value

class Lwjoinbinabp(CmdRtrn):
    ascii = " lwjoin"
    at = " AT+J"
    binary =  b"\xA6"

    def __init__(self, return_value):
        super().__init__("lwjoin", return_value)

    @property
    def return_value(self):
        if self._return_value is None:
            return
        if Cmd.mode == "binary":
            self._return_value = "1B 51 01 1B 53 4A 6F 69 6E 69 6E 67 20 74 68 65 20 4C 6F 52 61 57 41 4E 20 6E 65 74 77 6F 72 6B 2E 2E 2E 1B 54 1B 53 44 65 76 69 63 65 20 73 65 74 20 62 79 20 41 42 50"
            _return_value_parts = ["1B 50", self._return_value, "1B 54"]
            return " ".join(_return_value_parts)
        else:
            return self._return_value

class SetParser(Cmd):
    ascii = "sparser"
    at = "AT!P"
    binary = b"\xFB"

    def __init__(self):
        super().__init__("sparser", response="")

class SendBytes(Cmd):
    ascii = "sendb"
    at = "AT+X"
    binary = b"\x20"

    def __init__(self, length, string: str):
        self.length = length
        self.string = string
        super().__init__("sendb", args=(f"{self.length:02X}",))

    @property
    def command(self):
        if Cmd.mode == "binary":
            cmd = f"0x1B 0x2A "
            # binary_cmd = COMMAND_MAP[self._command]['binary']
            # cmd += f"0x{int(binary_cmd.hex(), 16):>02X} " if binary_cmd else ""
            cmd += f"0x{int(self.binary.hex(), 16):>02X} "
            for char in self.string.encode():
                cmd += f"0x{int(char):>02X} "
            cmd += "0x1B 0x42"
            return cmd
        return self.command_property()

class Reset(Cmd):
    ascii = " reset"
    at = " AT!!"
    binary =  b"\x12"

    def __init__(self):
        super().__init__("reset", response=None)