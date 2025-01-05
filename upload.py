"""
@file upload.py
@license MIT License
@copyright (c) 2025 Christopher A. Bohn
@author Christopher A. Bohn

@brief Python script to upload files to an RC2014 (or similar retrocomputers)

This script can transmit a text file as plaintext (no special encoding), or it
can package a text or binary file to a CP/M computer that has [Grant Searle's
`DOWNLOAD.COM`](http://searle.x10host.com/cpm/index.html) on its A: drive.

The nominal use is with one of [Spencer Owen's RC2014 computers](https://rc2014.co.uk/)
or a [similar retrocomputer](https://smallcomputercentral.com/).

There are a handful of options; however, a typical transmission (115.2 kilobaud,
file packaged for `DOWNLOAD.COM`) can be achieved by specifying only the port
(with the `-p` option) and the file to be uploaded.
"""
"""
MIT License

Copyright (c) 2025 Christopher A. Bohn

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import argparse
import functools
import os
import sys
from enum import StrEnum
from inspect import currentframe, getframeinfo
from time import sleep, time
from typing import Dict, List, NamedTuple, Optional, Union

import serial  # from the pyserial package (https://pyserial.readthedocs.io/)


class Statistics(StrEnum):
    FILE_BYTES = 'file bytes'
    TRANSMITTED_BYTES = 'transmitted bytes'
    INITIAL_CRLF_COUNT = 'CRLF count'  # TODO: work with the enum mentioned in the next TODO
    INITIAL_LFCR_COUNT = 'LFCR count'
    INITIAL_CR_COUNT = 'CR count'
    INITIAL_LF_COUNT = 'LF count'
    FINAL_NEWLINE_COUNT = 'line terminations'


statistics: Dict[str, Union[bool, int]] = {
    Statistics.FILE_BYTES: 0,
    Statistics.TRANSMITTED_BYTES: 0,
    Statistics.INITIAL_CRLF_COUNT: 0,
    Statistics.INITIAL_LFCR_COUNT: 0,
    Statistics.INITIAL_CR_COUNT: 0,
    Statistics.INITIAL_LF_COUNT: 0,
    Statistics.FINAL_NEWLINE_COUNT: 0,
}


class TransmissionFormat(StrEnum):
    PACKAGE = 'package'
    PLAINTEXT = 'plaintext'


class FileFormat(StrEnum):
    BINARY = 'binary'
    TEXT = 'text'


class File(NamedTuple):
    original_path: str
    target_name: str
    format: Optional[FileFormat]
    format_inferred: bool
    format_overridden: bool


class Port(NamedTuple):
    name: str
    flow_control_enabled: bool
    exclusive_port_access_mode: bool
    baud_rate: int


class Arguments(NamedTuple):
    files: List[File]
    serial_port: Optional[Port]
    ms_delay: int
    transmission_format: TransmissionFormat
    source_newlines: List[str]  # TODO: create enum
    target_newline: str
    user_number: int
    receive: bool


def upload_string(string: str, destination: Optional[serial.Serial], ms_delay: int, is_text_encoded_hex: bool = False):
    # TODO: split into `echo_string` and `upload_string`
    statistics[Statistics.TRANSMITTED_BYTES] += len(string)  # we are assuming 1 byte per character
    first_nibble: Optional[str] = None
    second_nibble: Optional[str] = None
    for character in string:
        if character == '\\':
            print('\\\\', end='')
        elif character == '\t':
            print('\\t', end='\t')
        elif character == '\r':
            print('\\r', end='')
        elif character == '\n':
            print('\\n', end='\n')
        elif is_text_encoded_hex:
            if first_nibble is None:
                first_nibble = character
                print(character, end='')
            elif second_nibble is None:
                second_nibble = character
                print(character, end='\n' if first_nibble + second_nibble == '0A' else ' ')
                first_nibble = None
                second_nibble = None
            else:
                raise RuntimeWarning(f'Reached unreachable code on line {getframeinfo(currentframe()).lineno} '
                                     f'(string={string}, character={character}, '
                                     f'first_nibble={first_nibble}, second_nibble={second_nibble})')
        else:
            print(character, end='')
        sys.stdout.flush()
        if destination is not None:
            destination.write(character.encode())
            destination.flush()
        sleep(ms_delay / 1000.0)


def upload_file(original_file: str, target_file: str, destination: Optional[serial.Serial],
                file_format: FileFormat, transmission_format: TransmissionFormat, ms_delay: int,
                user_number: int) -> None:
    # TODO: convert BBCMicro(\n\r / 0A0D) to Unix for conversion to CP/M
    if transmission_format == TransmissionFormat.PLAINTEXT:
        with open(original_file, 'rt') as source:
            for line in source.readlines():
                statistics[Statistics.FILE_BYTES] += len(line)  # we are assuming 1 byte per character
                # convert CP/M & MS-DOS & Windows to Unix, just in case it already has CP/M line terminations
                statistics[Statistics.INITIAL_CRLF_COUNT] += line.count('\r\n')
                line = line.replace('\r\n', '\n')
                # convert Apple ][ & classic Mac to Unix
                statistics[Statistics.INITIAL_CR_COUNT] += line.count('\r')
                line = line.replace('\r', '\n')
                # convert Unix to CP/M
                statistics[Statistics.INITIAL_LF_COUNT] += line.count('\n')  # over-count, corrected below
                line = line.replace('\n', '\r\n')
                statistics[Statistics.FINAL_NEWLINE_COUNT] += line.count('\r\n')
                upload_string(line, destination, ms_delay)
    elif transmission_format == TransmissionFormat.PACKAGE:
        with open(original_file, 'rb') as source:
            upload_string(f'A:DOWNLOAD {target_file}\r\nU{user_number}\r\n:', destination, ms_delay)
            byte_count: int = 0
            byte_sum: int = 0
            block_bytes: bytes = source.read(128)
            while block_bytes:
                statistics[Statistics.FILE_BYTES] += len(block_bytes)
                byte_count += len(block_bytes)
                byte_sum += functools.reduce(lambda a, b: a + b, block_bytes)
                block_string: str = ''.join(f'{byte:02x}'.upper() for byte in block_bytes)
                if file_format == FileFormat.TEXT:
                    # make sure lines have CP/M line terminations
                    # TODO: should this be parameterized to convert to Apple ][ line terminations?
                    # TODO: should this be parameterized to not convert at all?
                    #       Answer: see below
                    # convert CP/M & MS-DOS & Windows to Unix, just in case it already has CP/M line terminations
                    termination_count: int = block_string.count('0D0A')
                    block_string = block_string.replace('0D0A', '0A')
                    statistics[Statistics.INITIAL_CRLF_COUNT] += termination_count
                    byte_count -= termination_count
                    byte_sum -= termination_count * 0x0D
                    # convert Apple ][ & classic Mac to Unix
                    termination_count: int = block_string.count('0D')
                    block_string = block_string.replace('0D', '0A')
                    statistics[Statistics.INITIAL_CR_COUNT] += termination_count
                    byte_sum = byte_sum - termination_count * 0x0D + termination_count * 0x0A
                    # convert Unix to CP/M
                    termination_count: int = block_string.count('0A')
                    block_string = block_string.replace('0A', '0D0A')
                    statistics[Statistics.INITIAL_LF_COUNT] += termination_count  # over-count, corrected below
                    byte_count += termination_count
                    byte_sum += termination_count * 0x0D
                statistics[Statistics.FINAL_NEWLINE_COUNT] += block_string.count('0D0A')
                upload_string(block_string, destination, ms_delay)
                block_bytes = source.read(128)
            padding_needed: int = 128 - (byte_count % 128)
            if padding_needed > 0:
                byte_count += padding_needed
                upload_string(''.join('00' for _ in range(padding_needed)), destination, ms_delay)
            upload_string(f'>{(byte_count & 0xFF):02x}{(byte_sum & 0xFF):02x}'.upper(), destination, ms_delay)
    else:
        raise ValueError(f'No supported transmission format found in {transmission_format}.')
    # correct over-count
    statistics[Statistics.INITIAL_LF_COUNT] -= (
            statistics[Statistics.INITIAL_CRLF_COUNT] + statistics[Statistics.INITIAL_CR_COUNT])


def truncate_filename(filename: str) -> str:
    _, filename = os.path.split(filename)
    name, extension = os.path.splitext(filename)
    name = name.replace('.', '_')
    if len(name) > 8:
        name = name[:8].rstrip('_')
    if len(extension) > 4:
        extension = extension[:4]
    proposed_filename: str = f'{name}{extension}'.upper()
    new_filename: str = ''
    if proposed_filename == filename.upper():
        new_filename = proposed_filename
    else:
        while new_filename == '':
            user_filename_tokens: List[str]
            user_filename_tokens = (input(f'{filename} needs to be renamed to 8.3 format [{proposed_filename}]: ')
                                    .split('.'))
            if len(user_filename_tokens) == 0:
                new_filename = proposed_filename
            elif (1 <= len(user_filename_tokens) <= 2
                  and len(user_filename_tokens[0]) <= 8
                  and len(user_filename_tokens[1]) <= 3):
                new_filename = '.'.join(user_filename_tokens).upper()
            else:
                print(f'{'.'.join(user_filename_tokens).upper()} is not a valid filename.')
    return new_filename


def get_file_format(filename: str, file_format: Optional[str], transmission_format: TransmissionFormat) -> FileFormat:
    binary_file_extensions = {'.BIN', '.COM'}
    text_file_extensions = {'.ASM',
                            '.ADB', '.ADS',
                            '.BAK',
                            '.BAS',
                            '.C', '.H',
                            '.F', '.F77', '.FOR',
                            '.F', '.FTH', '.FS', '.4TH',
                            '.PAS',
                            '.TXT'}
    if transmission_format == TransmissionFormat.PLAINTEXT:
        f_format = FileFormat.TEXT
    elif file_format is not None:
        f_format = FileFormat(file_format)
    elif any(filename.upper().endswith(extension.upper()) for extension in text_file_extensions):
        f_format = FileFormat.TEXT
    elif any(filename.upper().endswith(extension.upper()) for extension in binary_file_extensions):
        f_format = FileFormat.BINARY
    else:
        try:
            with open(filename, 'rb') as file:
                first_kilobyte: bytes = file.read(1024)
                # TODO: what will this do with "extended ASCII"? ('utf-8' probably won't help)
                first_kilobyte.decode('ascii')
                # if the first KB can be decoded as text, then it's probably text
                f_format = FileFormat.TEXT
        except UnicodeDecodeError:
            f_format = FileFormat.BINARY
        except FileNotFoundError:
            # if the file doesn't exist, then the format doesn't matter
            # (the absence of the file is handled elsewhere)
            f_format = FileFormat.BINARY
    return f_format


def get_arguments() -> Arguments:
    # TODO: multiple source files
    # TODO: what if we don't want to convert line terminators? For package, no problem: send as binary. What about plaintext?
    #       Answer: --from-EOL abc def --to-EOL ghi (see https://en.wikipedia.org/wiki/Newline#Representation)
    # TODO: receive files (trigger https://github.com/RC2014Z80/RC2014/tree/master/CPM/UPLOAD.COM)
    argument_parser = argparse.ArgumentParser(
        prog='upload',
        description='Upload file to RC2014 or similar retrocomputer'
    )
    argument_parser.add_argument('source_file', type=str, nargs='+')
    argument_parser.add_argument('-p', '--port', type=str, default=None,
                                 help='The serial port for the serial connection (if omitted, rc2014upload will only print to the console, no transmission will be made).')
    argument_parser.add_argument('--flow-control', action=argparse.BooleanOptionalAction, default=True,
                                 help='Enable/disable flow control (default: enabled)')
    argument_parser.add_argument('--exclusive-port', action=argparse.BooleanOptionalAction, default=True,
                                 help='Enable/disable exclusive port access (default: enabled). '
                                      'n.b., neither shared nor exclusive access are guaranteed.')
    argument_parser.add_argument('-b', '--baud', type=int, default=115200,
                                 choices=[50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800, 9600, 14400,
                                          19200, 28800, 38400, 57600, 115200, 230400, 460800, 500000, 576000, 921600,
                                          1000000, 1152000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000],
                                 help='The baud rate for the serial connection (default: %(default)s). '
                                      'n.b., the RC2014 Dual Clock Module supports {4800, 9600, 14400, 19200, 38400, 57600, 115200}.')
    argument_parser.add_argument('-d', '--delay', type=int, default=0,
                                 help='The delay (in milliseconds) between characters.'
                                      'A delay shouldn\'t be necessary if flow control is enabled (default: %(default)s).')
    argument_parser.add_argument('-tf', '--transmission-format', choices=['package', 'plaintext'], default='package',
                                 help='The transmission format (default: %(default)s).')
    argument_parser.add_argument('-ff', '--file-format', choices=['binary', 'text'], default=None,
                                 help='The file format (default: inferred file type). '
                                      'n.b., if the transmission format is \'plaintext\', then the file format argument is ignored and replaced with \'text\'.')
    argument_parser.add_argument('-u', '--user', type=int, default=0,
                                 choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                                 help='The CP/M user number (default: %(default)s).')
    argument_parser.add_argument('-rx', '--receive', action='store_true',
                                 help='(placeholder--currently unused)\nIndicates that the file transfer will be to receive a file or files from the remote computer (default: the file transfer will be to transmit a file or files to the remote computer).')
    argument_parser.add_argument('--source-newlines', type=str, nargs='*',
                                 choices=['CR', 'LF', 'CRLF', 'LFCR', 'system'],
                                 default=['CR', 'LF', 'CRLF', 'LFCR'],
                                 help='(placeholder--currently uses only CR LF CRLF) One or more types of newlines to be converted to the destination computer\'s newline (default: %(default)s). '
                                      'An empty set of source-newlines indicates that no newline conversion should take place. '
                                      'When transmitting a file, \'system\' is the host computer\'s newline; when receiving a file, \'system\' is equivalent to CRLF (under the assumption that the remote computer runs CP/M). '
                                      'This option is applicable only to text files and is ignored for binary files.')
    argument_parser.add_argument('--target-newline', type=str, choices=['CR', 'LF', 'CRLF', 'LFCR', 'system'],
                                 default='system',
                                 help='(placeholder--currently uses only CRLF) The newline that the source-newlines will be converted to (default: %(default)s). '
                                      'When receiving a file, \'system\' is the host computer\'s newline; when transmitting a file, \'system\' is equivalent to CRLF (under the assumption that the remote computer runs CP/M). '
                                      'This option is applicable only to text files and is ignored for binary files.'
                                      'This option is ignored if the source-newlines is an empty set.')
    arguments = argument_parser.parse_args()
    transmission_format = TransmissionFormat(arguments.transmission_format)
    return Arguments(
        files=[File(original_path=source_file,
                    target_name=truncate_filename(source_file),
                    format=get_file_format(source_file, arguments.file_format, transmission_format),
                    format_inferred=(arguments.file_format is None),
                    format_overridden=(transmission_format == TransmissionFormat.PLAINTEXT
                                       and arguments.file_format is not None
                                       and arguments.file_format != 'text'))
               for source_file in arguments.source_file],
        serial_port=Port(name=arguments.port,
                         flow_control_enabled=arguments.flow_control,
                         exclusive_port_access_mode=arguments.exclusive_port,
                         baud_rate=arguments.baud) if arguments.port is not None else None,
        ms_delay=arguments.delay,
        transmission_format=transmission_format,
        source_newlines=arguments.source_newlines,
        target_newline=arguments.target_newline,
        user_number=arguments.user,
        receive=arguments.receive
    )


def main():
    arguments = get_arguments()
    start_time = time()
    if arguments.serial_port is not None:
        try:
            with serial.Serial(port=arguments.serial_port.name,
                               baudrate=arguments.serial_port.baud_rate,
                               rtscts=arguments.serial_port.flow_control_enabled,
                               exclusive=arguments.serial_port.exclusive_port_access_mode,
                               timeout=1) as destination:
                upload_file(original_file=arguments.files[0].original_path, target_file=arguments.files[0].target_name,
                            destination=destination, file_format=arguments.files[0].format,
                            transmission_format=arguments.transmission_format, ms_delay=arguments.ms_delay,
                            user_number=arguments.user_number)
        except serial.SerialException as e:
            print(f'Failed to write to {arguments.serial_port.name}: {e}')
            exit(1)
    else:
        upload_file(original_file=arguments.files[0].original_path, target_file=arguments.files[0].target_name,
                    destination=None, file_format=arguments.files[0].format,
                    transmission_format=arguments.transmission_format, ms_delay=arguments.ms_delay,
                    user_number=arguments.user_number)
    stop_time = time()
    sys.stdout.flush()
    if arguments.serial_port is None:
        print(f'\n\nSimulated {arguments.transmission_format} transmission of', end=' ',
              file=sys.stderr)
    else:
        print(f'\n\n{arguments.transmission_format.capitalize()} transmission of', end=' ',
              file=sys.stderr)
    print(f'{arguments.files[0].target_name}', end=' ',
          file=sys.stderr)
    if arguments.serial_port is not None:
        print(f'to {arguments.serial_port.name}', end=' ',
              file=sys.stderr)
    print(f'completed in {round(stop_time - start_time, 3)} seconds.',
          file=sys.stderr)
    print(f'\tFile format: {arguments.files[0].format} '
          f'(specified as {"inferred" if arguments.files[0].format_inferred else arguments.files[0].format})',
          file=sys.stderr)
    print(f'\tFile size:         {str(statistics[Statistics.FILE_BYTES]).rjust(9)}',
          file=sys.stderr)
    print(f'\tTransmission size: {str(statistics[Statistics.TRANSMITTED_BYTES]).rjust(9)}',
          file=sys.stderr)
    if arguments.files[0].format == FileFormat.TEXT:
        print(f'\tInitial CP/M  line terminations: {str(statistics[Statistics.INITIAL_CRLF_COUNT]).rjust(6)}',
              file=sys.stderr)
        print(f'\tInitial Apple line terminations: {str(statistics[Statistics.INITIAL_CR_COUNT]).rjust(6)}',
              file=sys.stderr)
        print(f'\tInitial Unix  line terminations: {str(statistics[Statistics.INITIAL_LF_COUNT]).rjust(6)}',
              file=sys.stderr)
        print(f'\tFinal   CP/M  line terminations: {str(statistics[Statistics.FINAL_NEWLINE_COUNT]).rjust(6)}',
              file=sys.stderr)


if __name__ == '__main__':
    main()
