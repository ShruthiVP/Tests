# Test executor script - Uses Python 3.5.3 or later
# Input is the text file with test commands to be send to
# connected devices and the serial ports of the devices.

import logging
import time
import sys
import csv

import serial
import pytest
import pytest_check as check
#import allure

#from tests.lora_commands.commands import Bandwidth, CodingRate, SpreadingFactor
from hello.commands import Cmd, CmdRtrn, SendBytes

######################
## GLOBAL VARIABLES ##
######################

# portlist = []  # List of serial port devices
test_lines_not_exec = []  # List of test not executed/recognised
test_file_name = None  # Test file
line_num = 0  # Test file line number
error_line = 0  # Error executing test line

# String terminator
end_string = "\r\n"

######################################
## CONSTANTS AND USEFUL DEFINITIONS ##
######################################

# Serial time out for the AM093 boards
serial_timeout = 0.2  # 0.1 timeout will lose some packages

# Special characters and strings
_comment_ = "//"
_printOutput_ = "!!"
_interp_command_ = "##"
_toConsoleIgnore_ = "%"
_declaration_ = "&"
_toDevice_ = ">"
_response_ = "~"
_event_ = "?"
_returned_ = "#"
_sendChar_ = "$"
_repeat_ = "@R"
_end_ = "@E"

# # Device response codes:
# responseCodes = (
#     "OK00>",
#     "ERFE>",
#     "ERFD>",
#     "ERFC>",
#     "ERFB>",
#     "ERFA>",
#     "ERF9>",
#     "ERF8>",
#     "ERF7>",
# )
# responseCodesStrings = (
#     "OK",
#     "Invalid command",
#     "Empty token",
#     "Malformed token",
#     "Parser timeout",
#     "Modem busy",
#     "Not enough arguments",
#     "Arguments out of bounds",
#     "Modem unable to execute command",
# )

# Interpreter commands
interp_command_enter = "ENTER"
interp_command_pause = "PAUSE"
interp_command_pause1 = "PAUSE1"


class Device(object):
    """
    Single test device class and its methods.
    """

    def __init__(self, newid, newport, newbaud, results_filepath="Results.csv"):
        """Properties of the device"""
        self.devtype = "Unknown"
        self.stackversion = None
        self.execversion = None
        self.id = newid
        self.port = newport
        self.baud = newbaud
        self.device = serial.Serial(newport, newbaud, timeout=serial_timeout)
        self.tfailed = []  # List with failed test lines
        self.joined = False  # Store whether the device has joined a LoRaWAN network
        self.last_command = None
        self.read_strings = []
        self.rssi_list = []
        self.transmit_status = []
        self.transmit_strings = []
        self.mode = "-"
        self.device_result = {
            "DeviceID": self.id,
            "DeviceType": self.devtype,
            "ExecVersion": self.execversion,
            "StackVersion": self.stackversion,
            "Mode": self.mode,
            "Command": self.last_command,
            "Actual": None,
            "Expected": None,
            "Result": None,
        }
        self.results_filepath = results_filepath
        with open(self.results_filepath, mode="w", newline="") as result_file:
            self.fieldnames = ['DeviceID', 'DeviceType', 'ExecVersion', 'StackVersion', 'Mode', 'Command', 'Actual',
                               'Expected', 'Result']
            self.result_writer = csv.DictWriter(result_file, fieldnames=self.fieldnames, restval='',
                                                extrasaction='ignore')
            self.result_writer.writeheader()

    #@allure.tag("version")
    def identify(self):
        """Get the details of the device connected to the port"""
        logging.info("DEVICE " + self.id + ", " + self.port)
        self.device.reset_input_buffer()
        self.device.write(str.encode("version" + end_string))
        time.sleep(serial_timeout)
        while self.device.in_waiting > 0:
            read_from_radio = bytes.decode(self.device.readline().strip())
            if read_from_radio.find("IDN: ") != -1:
                self.devtype = read_from_radio.split("IDN: ")[1]
                logging.info(read_from_radio)
                self.device_result.update(DeviceType=self.devtype)
            elif read_from_radio.find("EXECUTIVE VER:") != -1:
                self.execversion = read_from_radio.split("EXECUTIVE VER:")[1]
                logging.info(read_from_radio)
                self.device_result.update(ExecVersion=self.execversion)
            elif read_from_radio.find("RF STACK  VER:") != -1:
                self.stackversion = read_from_radio.split("RF STACK  VER:")[1]
                logging.info(read_from_radio)
                self.device_result.update(StackVersion=self.stackversion)

        print(" ")
        return self.device_result

    #@allure.tag("sending commands")
    def send_command(self, command):
        """Send the command to the device (>)"""
        time.sleep(serial_timeout)
        if self.joined and command in ["lwjoin", "lwstatus"]:
            pass
        else:
            self.device.reset_input_buffer()
            logging.info(f"[{self.id}]>>{command}")
            if command[0:2] != "0x":
                self.device.write(str.encode(command + end_string))
            else:
                bin_command = [int(x, 16) for x in command.split()]
                self.device.write(serial.to_bytes(bin_command))
            self.last_command = command
            self.device_result.update(
                {
                    "Command": command,
                    "Expected": None,
                    "Actual": None,
                    "Result": "Discard",
                }
            )
            return self.device_result

    #@allure.tag("read_response")
    def read_response(self, expected_response="OK00>", test_line="", check_response=True):
        """Read the response from the device (~)
        If the last command was successful the device responds with 'OK00'
        If unsuccessful the device responds with error codes"""
        wait = 0
        time.sleep(serial_timeout)

        if self.joined and self.last_command == "lwstatus":
            pass
        else:
            read_from_radio = bytes.decode(self.device.readline().strip())

            while read_from_radio == "" and wait < 60:
                # Wait for buffer to be populated
                print(".", end="", flush=True)
                read_from_radio = bytes.decode(self.device.readline().strip())
                wait = wait + 1
            logging.info(f"[{self.id}]<<{read_from_radio}")

            result = None

            if check_response:
                check.equal(read_from_radio, expected_response)

                if read_from_radio != expected_response:
                    result = "FAILED"
                    # logging.info(
                    #     f'\tFAILED : {read_from_radio} != {expected_response}, at line {line_num + 1}')
                    # # Store the line that failed
                    # self.tfailed.append((line_num + 1, test_line))

                    logging.info(f'\tFAILED : {read_from_radio} != {expected_response}')

                    if "sendb" in self.last_command:
                        self.transmit_status.append(["No-Tx", self.mode])
                else:
                    result = "PASSED"
                    logging.info('\tPASSED')
                    if "sendb" in self.last_command:
                        self.transmit_status.append(["Tx-Ok", self.mode])

            self.device_result.update(
                {"Expected": expected_response, "Actual": read_from_radio, "Result": result})  # , "Command": None})

            return self.device_result

   # @allure.tag("read event")
    def read_event(self, event, test_line=""):
        """Read the event message from the device (?)
        Event message and confirmation has a delay"""
        wait = 0

        if self.joined and event in ["Joining the LoRaWAN network...", "1B 53 4A 6F 69 6E 65 64 20 6E 65 74 77 6F 72 6B 1B 54"]:
            pass
        else:
            read_from_radio = bytes.decode(self.device.readline().strip())
            
            while (read_from_radio == "" and wait < 120):
                read_from_radio1 = self.device.readline().strip()

                if read_from_radio1.startswith(b'\x1b'):
                    read_from_radio = (read_from_radio1.hex(" ")).upper()
                else:
                    read_from_radio = bytes.decode(read_from_radio1)
                print(".", end="", flush=True)  # Wait for buffer to be populated
                wait = wait + 1
            print("\n" + "[" + self.id + "]<<" + read_from_radio)
            
            if (read_from_radio != event):
                result = "FAILED"
                print("\tFAILED " + read_from_radio + " != " + event + ", at line " + str(line_num+1))
                self.tfailed.append((line_num+1, test_line))  # Store the line that failed
            else:
                result = "PASSED"
        
            time.sleep(5)
            self.device_result.update(
                {"Expected": event, "Actual": read_from_radio, "Result": result})  # , "Command": None})
            return self.device_result

    def read_multiple_lines(self, return_value=None, test_line=""):
        """Read the value from the device (*)
        For commands requesting data, the device returns a value with mulitple lines"""
        time.sleep(serial_timeout)
        with open(self.results_filepath, mode="a", newline="") as result_file:
            result_writer = csv.DictWriter(result_file, fieldnames=self.fieldnames, restval='',
                                           extrasaction='ignore')
        lines = []
        read_from_radio = []
        wait = 0
        while True and wait < 60:
            read_from_radio1 = self.device.read_until(
                b"\n"
            )  # .decode('utf-8').strip()  # Read until newline
            if not read_from_radio1:
                break
            lines.append(read_from_radio1)
            wait += 1
        
        for i in lines:
                read_from_radio.append(bytes.decode(i, errors='ignore'))
        # read_from_radio = " ".join(read_from_radio)

        self.device_result.update({"Mode": self.mode})
        result = "PASSED"
        self.device_result.update(
                {"Expected": return_value, "Actual": read_from_radio, "Result": result}
            ) 
        return read_from_radio

   # @allure.tag("read_return_value")
    def read_return_value(self, return_value, test_line="", check_return=True):
        """Read the return value from the device (#)
        For commands requesting data, the device returns a value"""
        time.sleep(serial_timeout)
        wait = 0

        if self.joined and self.last_command == "lwstatus":
            pass
        else:
            read_from_radio1 = self.device.readline().strip()
            while read_from_radio1 == b'' and wait < 25:
                read_from_radio1 = self.device.readline().strip()
                # Wait for buffer to be populated
                print(".", end="", flush=True)
                wait = wait + 1
            if read_from_radio1.startswith(b"\x1b"):
                read_from_radio = (read_from_radio1.hex(" ")).upper()
            else:
                read_from_radio = bytes.decode(read_from_radio1)

            logging.info(f"[{self.id}]<<{read_from_radio}")
            if check_return:
                check.equal(read_from_radio, return_value)

            if self.last_command == "geta":
                if read_from_radio:
                    # check.equal(read_from_radio, return_value)
                    read_string = [read_from_radio, self.mode] if read_from_radio == return_value else [
                        read_from_radio + " --- fail", self.mode]
                else:
                    read_string = ["No-Rx", self.mode]
                self.read_strings.append(read_string)

            if return_value and read_from_radio != return_value:
                result = "FAILED"
                logging.info(f'\tFAILED : {read_from_radio} != {return_value}')
                # Store the line that failed
                # self.tfailed.append((line_num + 1, test_line))
            else:
                # check.equal(read_from_radio, return_value)
                result = "PASSED"
                logging.info('\tPASSED')
                self.joined = True if self.last_command == "lwstatus" else False
                if self.last_command == "rssi":
                    rssi = read_from_radio if self.read_strings[-1][0] != "No-Rx" else "--"
                    self.rssi_list.append(rssi)
                if self.last_command == "mode":
                    self.mode = read_from_radio
                    self.device_result.update({"Mode": self.mode})

            self.device_result.update(
                {"Expected": return_value, "Actual": read_from_radio, "Result": result})  # , "Command": None})
            return self.device_result

    #@allure.tag("sending string")
    def send_string(self, string_to_send, test_line=""):
        """Send a string to the device ($)"""
        read_from_radio = bytes.decode(self.device.readline().strip())
        while read_from_radio == "":
            read_from_radio = bytes.decode(self.device.readline().strip())

        if read_from_radio != _sendChar_:
            result = "FAILED"
            logging.info(
                f"\tFAILED : string send : Expected $; Rcvd << {read_from_radio}"
            )
            # Store the line that failed
            # self.tfailed.append((line_num + 1, test_line))
        else:
            self.device.reset_input_buffer()
            result = "PASSED"
            logging.info(f"[{self.id}]<<{read_from_radio}{string_to_send}")
            self.device.write(str.encode(string_to_send + end_string))
            self.transmit_strings.append(string_to_send)

        # time.sleep(2)
        self.device_result.update(
            {"Expected": "$", "Actual": read_from_radio, "Result": result}
        )
        return self.device_result

    def flush_buffer(self):
        """Wait and clear the responses and or returns from the device (%)"""
        time.sleep(2)
        self.device.reset_input_buffer()
        logging.info("-Flush buffer-")
        self.mode = "-"
        self.device_result.update({"Mode": self.mode})
        command = self.device_result.get("Command")
        return {"DeviceID": self.id, "Command": command, "Result": None}

    def close(self):
        """Close the port the device is connected to"""
        self.device.close()

    def send_receive(self, command):
        logging.info(f"Send/Receive [{self.id}]: {command}")

        with open(self.results_filepath, mode="a", newline="") as result_file:
            result_writer = csv.DictWriter(result_file, fieldnames=self.fieldnames, restval='',
                                           extrasaction='ignore')
            if command.command is not None:
                device_result = self.send_command(command.command)
                if device_result["Result"] != "Discard":
                    result_writer.writerow(device_result)

                if Cmd.mode != "binary" and type(command) is SendBytes:
                    device_result = self.send_string(command.string)
                    if device_result["Result"] != "Discard":
                        result_writer.writerow(device_result)

            if isinstance(command, CmdRtrn):
                check_return = False if command.return_value is None else True
                device_result = self.read_return_value(command.return_value, check_return=check_return)
                if device_result["Result"] != "Discard":
                    result_writer.writerow(device_result)

            if command.response:
                if Cmd.mode == "binary":
                    device_result = self.read_return_value(command.response)
                else:
                    device_result = self.read_response(command.response)
                if device_result["Result"] != "Discard":
                    result_writer.writerow(device_result)


class TestDevices(object):
    """
    Container of all devices to be tested.
    """

    def __init__(self, port_list):
        self.evklist = []
        self.evknum = 0
        self.evkbnum = 1

        self.port_list = port_list

    def clean(self):
        for devptr in self.evklist:
            devptr.close()

    def newevk(self, newID):
        if self.evknum >= len(self.port_list):
            raise Exception(
                f"No serial ports available: evknum {self.evknum}, port_list {self.port_list}"
            )
        else:
            self.evklist.append(
                Device(newID, self.port_list[self.evknum],
                       self.port_list[self.evkbnum])
            )
            logging.info(f"{self.port_list[self.evkbnum]}")
            self.evknum = self.evknum + 2
            self.evkbnum = self.evkbnum + 2

    def getdev(self, ID):
        for devptr in self.evklist:
            if devptr.id == ID:
                return devptr
        raise Exception("Device doesn't exist")

    def testsummary(self):
        """Summary of test results for a device"""
        failures = False

        for devptr in self.evklist:
            summary_line = f"DEVICE {devptr.id}, {devptr.devtype}, {devptr.port}. "
            if len(devptr.tfailed) == 0:
                logging.info(f"{summary_line}PASSED")
            else:
                failures = True
                logging.info("--------- Failures ---------")
                logging.info("--- No: ---\t--- Line ---")

                for failed_lines in devptr.tfailed:
                    logging.info(f"{failed_lines[0]}\t\t{failed_lines[1]}")

            if devptr.transmit_status and (
                len(devptr.transmit_strings) == len(devptr.transmit_status)
            ):
                number_sent = 0
                for status in devptr.transmit_status:
                    if status[0] != "No-Tx":
                        number_sent = number_sent + 1
                logging.info(
                    f"------- Tx and Success -------\t{number_sent} of {len(devptr.transmit_strings)} sent"
                )
                logging.info("-- Status -- \t ----  msg  ----    ---- mode ----")
                length = len(devptr.transmit_strings)
                for i in range(length):
                    logging.info(
                        f"{devptr.transmit_status[i][0].ljust(16)}|"
                        + f"{devptr.transmit_strings[i].center(16)}|"
                        + f"{devptr.transmit_status[i][1].center(16)}"
                    )

            if devptr.read_strings and (
                len(devptr.read_strings) == len(devptr.rssi_list)
            ):
                number_rcvd = 0
                for status in devptr.read_strings:
                    if status[0] != "No-Rx" and "fail" not in status[0]:
                        number_rcvd = number_rcvd + 1
                logging.info(
                    f"-------- Rx and RSSI --------\t{number_rcvd} of {len(devptr.read_strings)} received"
                )
                logging.info("--- Msg --- \t ---- rssi ----    ---- mode ----")
                length = len(devptr.read_strings)
                col_width = max(
                    16, max([len(x) for x in [s[0]
                            for s in devptr.read_strings]])
                )  # width of first column for printing
                for i in range(length):
                    logging.info(
                        f"{devptr.read_strings[i][0].ljust(col_width)}|"
                        + f"{devptr.rssi_list[i].center(16)}|"
                        + f"{devptr.read_strings[i][1].center(16)}"
                    )

            logging.info("~" * 55)
        return failures


class FlowTestExecutor:
    def __init__(self, name, directives, port_list):
        self.name = name
        self.directives = directives
        self.port_list = port_list

        self.test = TestDevices(self.port_list)
        self.devices = []

    @staticmethod
    def interpreter_command(icommand):
        if icommand == interp_command_enter:
            input("\n## Press Enter to continue... ##")
            print(" ")
        elif icommand == interp_command_pause:
            wait = 0
            while wait < 120:
                print(".", end="", flush=True)  # Wait
                time.sleep(0.03)
                wait = wait + 1
            print("")
        elif icommand == interp_command_pause1:
            wait = 0
            while wait < 120:
                print(".", end="", flush=True)  # Wait
                time.sleep(0.05)
                wait = wait + 1
            print("")
        else:
            print("Unknown interpreter command")

    def process_line(self, line_num, test_line):
        """Function to read and process the testfile"""

        if test_line.strip() == "":  # Ignore blank lines
            return {"Result": "Discard"}  # return 0

        if test_line[:2] == _comment_:  # Ignore comments
            pass
        elif test_line[:2] == _interp_command_:
            logging.info(test_line.strip())
            self.interpreter_command(test_line[2:].strip())
        elif (
            test_line.strip()[:2] == _printOutput_
        ):  # Print the read string to o/p file/screen
            logging.info(test_line.strip())
        elif test_line[:2] == _repeat_:
            logging.info("---------Repeat---------")
        elif test_line[:2] == _end_:
            logging.info("----------End-----------")
        elif test_line.find("[") < test_line.find("]"):  # Device number and action
            device_id, device_action = test_line.split(
                "]"
            )  # Identify device number and operation to perform
            device_id = device_id.split("[")[1]
            return self.device_operation(device_id, device_action, test_line)
        else:  # Error in processing the line
            logging.info(f"Unknown line {line_num}: {test_line}")
            test_lines_not_exec.append(line_num)

        return {"Result": "Discard"}  # return 0

    def device_operation(self, device_id, device_action, test_line):
        """Operation to be performed by the device."""

        if device_action[0] == _declaration_:  # New device found
            # logging.info(test_line)
            logging.info("New device found:")
            self.test.newevk(device_id)

            device_result = self.test.getdev(device_id).identify()

        elif device_action[0] == _toDevice_:  # Command for the device to execute
            device_action = device_action[1:].strip()
            device_result = self.test.getdev(
                device_id).send_command(device_action)
        elif device_action[0] == _response_:  # Response to command from the device
            device_result = self.test.getdev(device_id).read_response(
                test_line=test_line
            )
        elif device_action[0] == _event_:  # Event message from the device
            event = device_action[1:].strip()
            device_result = self.test.getdev(device_id).read_event(
                event, test_line=test_line
            )
        elif device_action[0] == _returned_:  # Return value from the device
            return_value = device_action[1:].strip()
            device_result = self.test.getdev(device_id).read_return_value(
                return_value, test_line=test_line
            )
        elif (
            device_action[0] == _sendChar_
        ):  # String for the device to send over the radio
            device_action = device_action[1:].strip()
            device_result = self.test.getdev(device_id).send_string(
                device_action, test_line=test_line
            )
        elif (
            device_action[0] == _toConsoleIgnore_
        ):  # Command to execute but ignore the response
            device_action = device_action[1:].strip()
            self.test.getdev(device_id).send_command(device_action)
            device_result = self.test.getdev(device_id).flush_buffer()
        else:
            logging.warning("Unknown operation")
            device_result = {"Operation": "Unknown"}

        return device_result

    def run(self, directives=[]):
        test_time = time.strftime("%d-%m-%Y_%H-%M-%S")

        # logging.info(test_file_name)
        # testfname = self.test_file_name.split(".")[0]
        # logging.info(testfname)
        #
        # try:
        #     f = open(self.test_file_name, 'r')
        # except:
        #     logging.error("Error: Could not open '" + self.test_file_name + "' file")
        #     raise

        repeat = False
        repeat_lines = []

        csv_result_file = "Result_" + test_time + "_" + self.name + ".csv"

        with open(csv_result_file, mode="w", newline="") as result_file:

            fieldnames = [
                "DeviceID",
                "DeviceType",
                "ExecVersion",
                "StackVersion",
                "Mode",
                "Command",
                "Actual",
                "Expected",
                "Result",
            ]
            result_writer = csv.DictWriter(
                result_file, fieldnames=fieldnames, restval="", extrasaction="ignore"
            )
            result_writer.writeheader()

            try:
                for line_num, test_line in enumerate(self.directives):
                    if "REPEAT" in test_line:
                        repeat_times = int(test_line.partition(" ")[2].strip())
                        repeat = True
                        continue
                    if repeat == True:
                        if "END" in test_line:
                            repeat = False
                            logging.info(
                                "\n>>>>>> REPEATING ",
                                int(repeat_times),
                                " times >>>>>>",
                            )
                            for i in range(repeat_times):
                                for line_num, test_line in repeat_lines:
                                    line_result = self.process_line(
                                        line_num + 1, test_line
                                    )
                                    if line_result["Result"] == "Discard":
                                        pass
                                    else:
                                        result_writer.writerow(line_result)
                            repeat_lines.clear()
                            logging.info("\n>>>>>> END REPEAT <<<<<<")
                            continue
                        else:
                            repeat_lines.append((line_num, test_line))
                            continue
                    line_result = self.process_line(line_num + 1, test_line)
                    if line_result.get('Result') == "Discard" or line_result is None:
                        pass
                    else:
                        result_writer.writerow(line_result)

            except:
                logging.error(
                    f"-------Error at line-------- {line_num + 1}{test_line}")
                error_line = 1
                raise

        # f.close()

        logging.info("=======================================================")
        logging.info(f"SUMMARY: {test_file_name}")
        failures_present = self.test.testsummary()
        if len(test_lines_not_exec) != 0:
            logging.warning(
                "WARNING! Some commands might not have been executed at lines:")
            logging.info(" ".join(map(str, test_lines_not_exec)))

        self.test.clean()

    def test_summary(self):
        """Summary of test results for a device"""
        failures = False

        for device in self.devices:
            summary_line = f"DEVICE {device.id}, {device.devtype}, {device.port}. "
            if len(device.tfailed) == 0:
                logging.info(f"{summary_line}PASSED")
            else:
                failures = True
                logging.info("--------- Failures ---------")
                logging.info("--- No: ---\t--- Line ---")

                for failed_lines in device.tfailed:
                    logging.info(f"{failed_lines[0]}\t\t{failed_lines[1]}")

            if device.transmit_status and (
                len(device.transmit_strings) == len(device.transmit_status)
            ):
                number_sent = 0
                for status in device.transmit_status:
                    if status[0] != "No-Tx":
                        number_sent = number_sent + 1
                logging.info(
                    f"------- Tx and Success -------\t{number_sent} of {len(device.transmit_strings)} sent"
                )
                logging.info("-- Status -- \t ----  msg  ----    ---- mode ----")
                length = len(device.transmit_strings)
                for i in range(length):
                    logging.info(
                        f"{device.transmit_status[i][0].ljust(16)}|"
                        + f"{device.transmit_strings[i].center(16)}|"
                        + f"{device.transmit_status[i][1].center(16)}"
                    )

            if device.read_strings and (
                len(device.read_strings) == len(device.rssi_list)
            ):
                number_rcvd = 0
                for status in device.read_strings:
                    if status[0] != "No-Rx" and "fail" not in status[0]:
                        number_rcvd = number_rcvd + 1
                logging.info(
                    f"-------- Rx and RSSI --------\t{number_rcvd} of {len(device.read_strings)} received"
                )
                logging.info("--- Msg --- \t ---- rssi ----    ---- mode ----")
                length = len(device.read_strings)
                col_width = max(
                    16, max([len(x) for x in [s[0]
                            for s in device.read_strings]])
                )  # width of first column for printing
                for i in range(length):
                    logging.info(
                        f"{device.read_strings[i][0].ljust(col_width)}|"
                        + f"{device.rssi_list[i].center(16)}|"
                        + f"{device.read_strings[i][1].center(16)}"
                    )

            logging.info("~" * 55)
        return failures

# @pytest.fixture
# def executor(common_commands, stack_commands, port_list, bandwidth, coding_rate, spreading_factor):
#     test_name = f'lora-sb_{bandwidth}_sg_{coding_rate}_sf_{spreading_factor}'
#     test_directives = common_commands + stack_commands
#     return FlowTestExecutorDict(test_name, test_directives, port_list)


# @pytest.fixture
# def test_name(bandwidth, coding_rate, spreading_factor):
#     return f'lora-sb_{bandwidth}_sg_{coding_rate}_sf_{spreading_factor}'


@pytest.fixture
def port_list(config_data):
    return [
        config_data["device1"]["port"],
        config_data["device1"]["baudrate"],
        config_data["lora_device_2"]["port"],
        config_data["lora_device_2"]["baudrate"],
    ]
