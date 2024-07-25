"""sample test"""
import unittest

from hello import hello

import time
import logging

import pytest

from hello.test_executor import Device
#add Gevent command
from hello.commands import Cmd, SendBytes, Lorawan, Stack, Ping, Sevent, Sconfirm, Confirm, Devid, \
    Sappeui, Gappeui, Sappkey, Gappkey, Sotaa, Gotaa, Lwjoin, Lwjoinbin, WakeUp, SetParser, Lwstatus, Sappskey, Gappskey, \
        Snwkskey, Gnwkskey, Sdevaddr, Gdevaddr, Lwjoinbinabp


class TestHello(unittest.TestCase):
    """sample test"""

    def test_world(self):
        """sample test"""
        self.assertEqual(hello('world'), 'hello world')

    def test_world_unicode(self):
        """sample test with unicode"""
        self.assertEqual(hello(u'world'), u'hello world')


class Testworld(unittest.TestCase):

    def test_hello(self):
        """sample test hello"""
        self.assertEqual(hello('hello'), 'hello hello')


def pause(ticks=120, period=0.03):
    wait = 0
    while wait < ticks:
        print(".", end="", flush=True)  # Wait
        time.sleep(period)
        wait = wait + 1
    print("")


def detect_parser_mode(device: Device):
    device.send_command("ping")
    result = device.read_return_value("PONG!", check_return=False)
    logging.info(f"ASCII ping: port = {device.port}, result = {result}")
    if result["Actual"] == "":
        device.send_command("0x1B 0x2A 0x11 0x1B 0x42")
        result = device.read_return_value("1B 50 1B 51 01", check_return=False)
        logging.info(f"Binary ping: port = {device.port}, result = {result}")
        if result["Actual"] == "1B 50 1B 51 01":
            return "binary"
    elif result["Actual"] == "PONG!":
        return "ascii"
    result = device.read_response(check_response=False)
    logging.info(f"Read response: port = {device.port}, result = {result}")


def set_parser_mode(device, current_mode, target_mode):
    if current_mode == "ascii" or current_mode == "at":
        if target_mode == "binary":
            old_mode = Cmd.mode
            Cmd.mode = "ascii"
            device.send_receive(SetParser())
            Cmd.mode = old_mode
    elif current_mode == "binary":
        if target_mode == "ascii" or target_mode == "at":
            old_mode = Cmd.mode
            Cmd.mode = "binary"
            device.send_receive(SetParser())
            device.read_return_value("1B 50 1B 51 01", check_return=False)
            Cmd.mode = old_mode

            device.send_receive(WakeUp())
            device.send_receive(WakeUp())
            device.send_receive(WakeUp())
            device.send_receive(WakeUp())
            device.read_response()


class TestLorawanCommands(pytest):
    @pytest.fixture
    def devices(self, config_data, results_filepath):
        dev1 = Device("1", config_data['device1']['port'], config_data['device1']['baudrate'],
                      results_filepath=results_filepath)
        dev1.identify()
        dev2 = Device("2", config_data['device2']['port'], config_data['device2']['baudrate'],
                      results_filepath=results_filepath)
        dev2.identify()
        return dev1, dev2

    @pytest.fixture
    def device1(self, devices):
        return devices[0]

    @pytest.fixture
    def device2(self, devices):
        return devices[1]

    @pytest.fixture(autouse=True)
    def parser(self, parser_mode):
        Cmd.mode = "ascii"

        def _parser():
            Cmd.mode = parser_mode
            return Cmd.mode

        return _parser

    @pytest.fixture(autouse=True)
    def wake_devices(self, device1, parser):
        device1.send_receive(WakeUp())
        device1.send_receive(WakeUp())
        device1.send_receive(WakeUp())
        device1.send_receive(WakeUp())
        device1.send_receive(WakeUp())
        device1.send_receive(WakeUp())
        device1.send_receive(WakeUp())
        device1.send_receive(WakeUp())

        config_mode = parser()
        set_parser_mode(device1, detect_parser_mode(device1), config_mode)

    @pytest.fixture(autouse=True)
    def prepare_stack(self, wake_devices, device1):
        device1.send_receive(Lorawan())
        device1.send_receive(Stack("lorawan"))

        device1.send_receive(Ping("PONG!"))

        device1.send_receive(Sevent(enabled=False))
        #device1.send_receive(Gevent(enabled=False))

        device1.send_receive(Sevent(enabled=True))
        #device1.send_receive(Gevent(enabled=True))

        device1.send_receive(Sconfirm(enabled=False))
        device1.send_receive(Confirm(enabled=False))

        device1.send_receive(Sconfirm(enabled=True))
        device1.send_receive(Confirm(enabled=True))

        device1.send_receive(Devid("97 4F 2F 6C E9 02 BE 77"))

    def test_otaa_lwjoin(self, device1,parser_mode):
        device1.send_receive(Sappeui("12 34 56 78 12 34 56 78"))

        device1.send_receive(Gappeui("12 34 56 78 12 34 56 78"))

        device1.send_receive(Sappkey("CD C2 5A BD 81 63 A9 DA 88 EB 4B 16 8A E4 9E BD"))
        device1.send_receive(Gappkey("CD C2 5A BD 81 63 A9 DA 88 EB 4B 16 8A E4 9E BD"))
        device1.send_receive(Sotaa(enabled=True))
        device1.send_receive(Gotaa(enabled=True))

        if parser_mode == "ascii" or parser_mode == "at":
            device1.send_receive(Lwjoin())
            device1.read_event("EVENT Joining the LoRaWAN network...")
            pause()
            device1.read_event("EVENT Joined network")
            pause()
            device1.send_receive(Lwstatus("01"))
            device1.send_receive(SendBytes(5, "12345"))
            device1.read_event("EVENT Confirmed message transmitted")
        elif parser_mode == "binary":
            device1.send_receive(Lwjoinbin("1B 50 1B 51 01 1B 53 4A 6F 69 6E 69 6E 67 20 74 68 65 20 4C 6F 52 61 57 41 4E 20 6E 65 74 77 6F 72 6B 2E 2E 2E 1B 54"))
            device1.read_event("1B 53 4A 6F 69 6E 65 64 20 6E 65 74 77 6F 72 6B 1B 54")
            pause()
            device1.send_receive(Lwstatus(1))
            device1.send_receive(SendBytes(5, "12345"))
            device1.read_event("1B 53 43 6F 6E 66 69 72 6D 65 64 20 6D 65 73 73 61 67 65 20 74 72 61 6E 73 6D 69 74 74 65 64 1B 54")