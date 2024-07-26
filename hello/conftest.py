import re
import os.path
import logging
import time
from pathlib import Path

import allure
import numpy as np
import pandas as pd
import pytest
import yaml


cur_path = os.path.dirname(os.path.realpath(__file__))
log_path = os.path.join(cur_path, "logs")
if not os.path.exists(log_path):
    os.mkdir(log_path)
log_time = time.strftime('%Y-%m-%d_%H-%M-%S')
log_dir = os.path.join(log_path, log_time)
if not os.path.exists(log_dir):
    os.mkdir(log_dir)


LOG_DIR = log_dir


def pytest_addoption(parser):
    parser.addoption(
        "--com-port",
        action="store",
        default=None,
        help="COM port to pass to test functions",
        type=valid_com_port
    )
    # parser.addoption(
    #     "--lorawan-device-eui",
    #     action="store",
    #     default=None,
    #     help="Device EUI to set when running LoRaWAN tests",
    #     type=valid_lorawan_device_eui
    # )

    parser.addoption(
        "--lorawan-application-key",
        action="store",
        default=None,
        help="Application key for LoRaWAN tests",
        type=valid_lorawan_application_key
    )

    parser.addoption(
        '--configuration',
        action='store',
        default=None,
        help='Path to configuration file',
        type=valid_config_file
    )

    parser.addoption(
        "--parser_mode",
        action="store",
        default="ascii",
        choices=["ascii", "at", "binary"],
        help="DUT parser mode (human readable: ascii / at, machine readable: binary)",
    )


def valid_com_port(value):
    if not value.startswith("COM") and not value.startswith("/dev/tty"):
        raise pytest.UsageError("COM port must be specified like COMX")
    return value


def valid_lorawan_device_eui(value):
    if not re.match("[A-F0-9]{16}", value):
        raise pytest.UsageError(
            "LoRaWAN device EUI must be specified like XXXXXXXXXXXXXXXX")
    return value


def valid_lorawan_application_key(value):
    hex_bytes = value.split()
    if len(hex_bytes) != 16:
        raise pytest.UsageError(
            "LoRaWAN application key must be 16 hex-encoded bytes")
    return value


def valid_config_file(value):
    if not os.path.isfile(value):
        raise pytest.UsageError(
            f'Configuration file path is not a file: {value}')
    return value


@pytest.fixture(scope="session", autouse=True)
def com_port(request):
    return request.config.getoption("--com-port")


@pytest.fixture(scope="session")
def lorawan_application_key(request):
    application_key = request.config.getoption("--lorawan-application-key")
    logging.info(f"LoRaWAN application key: {application_key}")
    return application_key


@pytest.fixture(scope='session')
def config_data(request):
    config_file = request.config.getoption('--configuration')
    logging.info(f'Configuration file path: {config_file}')
    with open(config_file) as file:
        data = yaml.safe_load(file)
        return data


@pytest.fixture(scope="session")
def parser_mode(request):
    parser = request.config.getoption("--parser_mode")
    logging.info(f"Parser mode: {parser}")
    return parser


@pytest.fixture
def log_directory():
    return LOG_DIR


@pytest.fixture
def test_name(request):
    return request.node.name


@pytest.fixture
def results_filepath(log_directory, test_name):
    filepath = os.path.join(LOG_DIR, f"{test_name}_{log_time}.csv")
    yield filepath
    df = pd.read_csv(filepath)
    df = df.replace({np.nan: None})
    df = df.to_html(index=False)
    html_filepath = filepath.replace(".csv", ".html")
    with open(html_filepath, "w") as f:
        f.write(df)
    with allure.step("html results files"):
        allure.attach.file(
            html_filepath, attachment_type=allure.attachment_type.HTML
        )


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_setup(item):
    global LOG_DIR

    test_name = item._request.node.name
    LOG_DIR = _log_dir = os.path.join(log_dir, test_name)
    if not os.path.exists(_log_dir):
        os.mkdir(_log_dir)
    config = item.config
    logging_plugin = config.pluginmanager.get_plugin("logging-plugin")
    filename = Path(_log_dir, f"{test_name}_{log_time}.log")
    logging_plugin.set_log_path(str(filename))
    yield
