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
from typing import Dict, Iterable, List, Optional, Set, Union

import serial  # from the pyserial package (https://pyserial.readthedocs.io/)


class FormatSpecification(StrEnum):
    PACKAGE = 'package'
    PLAINTEXT = 'plaintext'
    BINARY = 'binary'
    TEXT = 'text'


class Statistics(StrEnum):
    FILE_BYTES = 'file bytes'
    TRANSMITTED_BYTES = 'transmitted bytes'
    INITIAL_CRLF_COUNT = 'CRLF count'
    INITIAL_CR_COUNT = 'CR count'
    INITIAL_LF_COUNT = 'LF count'
    FINAL_LINE_TERMINATION_COUNT = 'line terminations'
    MISMATCHED_FORMATS = 'mismatched formats'


statistics: Dict[str, Union[bool, int]] = {
    Statistics.FILE_BYTES: 0,
    Statistics.TRANSMITTED_BYTES: 0,
    Statistics.INITIAL_CRLF_COUNT: 0,
    Statistics.INITIAL_CR_COUNT: 0,
    Statistics.INITIAL_LF_COUNT: 0,
    Statistics.FINAL_LINE_TERMINATION_COUNT: 0,
    Statistics.MISMATCHED_FORMATS: False,
}


def upload_string(string: str, destination: Optional[serial.Serial], ms_delay: int, is_text_encoded_hex: bool = False):
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


def upload_file(filename: str, destination: Optional[serial.Serial],
                formats: Iterable[FormatSpecification], ms_delay: int, user_number: int) -> None:
    if FormatSpecification.PLAINTEXT in formats:
        with open(filename, 'rt') as source:
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
                statistics[Statistics.FINAL_LINE_TERMINATION_COUNT] += line.count('\r\n')
                upload_string(line, destination, ms_delay)
    elif FormatSpecification.PACKAGE in formats:
        with open(filename, 'rb') as source:
            upload_string(f'A:DOWNLOAD {filename}\r\nU{user_number}\r\n:', destination, ms_delay)
            byte_count: int = 0
            byte_sum: int = 0
            block_bytes: bytes = source.read(128)
            while block_bytes:
                statistics[Statistics.FILE_BYTES] += len(block_bytes)
                byte_count += len(block_bytes)
                byte_sum += functools.reduce(lambda a, b: a + b, block_bytes)
                block_string: str = ''.join(f'{byte:02x}'.upper() for byte in block_bytes)
                if FormatSpecification.TEXT in formats:
                    # make sure lines have CP/M line terminations
                    # TODO: should this be parameterized to convert to Apple ][ line terminations?
                    # TODO: should this be parameterized to not convert at all?
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
                statistics[Statistics.FINAL_LINE_TERMINATION_COUNT] += block_string.count('0D0A')
                upload_string(block_string, destination, ms_delay)
                block_bytes = source.read(128)
            padding_needed: int = 128 - (byte_count % 128)
            if padding_needed > 0:
                byte_count += padding_needed
                upload_string(''.join('00' for _ in range(padding_needed)), destination, ms_delay)
            upload_string(f'>{(byte_count & 0xFF):02x}{(byte_sum & 0xFF):02x}'.upper(), destination, ms_delay)
    else:
        raise ValueError(f'No supported transmission format found in {formats}.')
    # correct over-count
    statistics[Statistics.INITIAL_LF_COUNT] -= (
            statistics[Statistics.INITIAL_CRLF_COUNT] + statistics[Statistics.INITIAL_CR_COUNT])


def get_formats(filename: str, transmission_format: str, file_format: Optional[str]) -> Set[FormatSpecification]:
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
    formats: Set[FormatSpecification]
    if transmission_format == FormatSpecification.PLAINTEXT:
        if file_format is not None and file_format != 'text':
            statistics[Statistics.MISMATCHED_FORMATS] = True
        formats = {FormatSpecification.PLAINTEXT, FormatSpecification.TEXT}
    elif file_format is not None:
        formats = {FormatSpecification(transmission_format), FormatSpecification(file_format)}
    elif transmission_format == FormatSpecification.PLAINTEXT:
        formats = {FormatSpecification.PLAINTEXT, FormatSpecification.TEXT}
    elif any(filename.upper().endswith(extension.upper()) for extension in text_file_extensions):
        formats = {FormatSpecification.PACKAGE, FormatSpecification.TEXT}
    elif any(filename.upper().endswith(extension.upper()) for extension in binary_file_extensions):
        formats = {FormatSpecification.PACKAGE, FormatSpecification.BINARY}
    else:
        with open(filename, 'rb') as file:
            first_kilobyte: bytes = file.read(1024)
            try:
                first_kilobyte.decode('utf-8')  # TODO: should we use 'ascii' instead?
                # if the first KB can be decoded as text, then it's probably text
                formats = {FormatSpecification.PACKAGE, FormatSpecification.TEXT}
            except UnicodeDecodeError:
                formats = {FormatSpecification.PACKAGE, FormatSpecification.BINARY}
    return formats


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


def main():
    argument_parser = argparse.ArgumentParser(
        prog='upload',
        description='Upload file to RC2014 or similar retrocomputer'
    )
    argument_parser.add_argument('source_file')
    argument_parser.add_argument('-p', '--port', type=str, default=None,
                                 help='The serial port for the serial connection (if omitted, rc2014upload will only print to the console, no transmission will be made)')
    argument_parser.add_argument('--flow-control', action=argparse.BooleanOptionalAction, default=True,
                                 help='Enable/disable flow control (default: enabled)')
    argument_parser.add_argument('-b', '--baud', type=int, default=115200,
                                 choices=[50, 75, 110, 134, 150, 200, 300, 600, 1200, 1800, 2400, 4800, 9600, 14400,
                                          19200, 28800, 38400, 57600, 115200, 230400, 460800, 500000, 576000, 921600,
                                          1000000, 1152000, 1500000, 2000000, 2500000, 3000000, 3500000, 4000000],
                                 help='The baud rate for the serial connection (default: %(default)s) -- n.b., the '
                                      'RC2014 Dual Clock Module supports {4800, 9600, 14400, 19200, 38400, 57600, 115200}')
    argument_parser.add_argument('-d', '--delay', type=int, default=0,
                                 help='The delay (in milliseconds) between characters, shouldn\'t be necessary '
                                      'if flow control is enabled (default: %(default)s)')
    argument_parser.add_argument('-tf', '--transmission-format', choices=['package', 'plaintext'], default='package',
                                 help='The transmission format (default: %(default)s)')
    argument_parser.add_argument('-ff', '--file-format', choices=['binary', 'text'], default=None,
                                 help='The file format (default: inferred file type) -- n.b., if the transmission format'
                                      ' is \'plaintext\', then the file format argument is ignored and replaced with \'text\'')
    argument_parser.add_argument('-u', '--user', type=int, default=0,
                                 choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                                 help='The CP/M user number (default: %(default)s)')
    arguments = argument_parser.parse_args()
    source_file = truncate_filename(arguments.source_file)
    formats: Set[FormatSpecification] = get_formats(source_file,
                                                    arguments.transmission_format,
                                                    arguments.file_format)
    start_time = time()
    if arguments.port is not None:
        try:
            # TODO: attempt to share the port (exclusive==False -- POSIX only) (doesn't work with `screen` but we can make it an option anyway)
            with serial.Serial(arguments.port,
                               baudrate=arguments.baud,
                               rtscts=arguments.flow_control,
                               timeout=1) as destination:
                upload_file(filename=source_file, destination=destination, formats=formats,
                            ms_delay=arguments.delay, user_number=arguments.user)
        except serial.SerialException as e:
            print(f'Failed to write to {arguments.port}: {e}')
            exit(1)
    else:
        upload_file(filename=source_file, destination=None, formats=formats,
                    ms_delay=arguments.delay, user_number=arguments.user)
    stop_time = time()
    sys.stdout.flush()
    if arguments.port is None:
        print(f'\n\nSimulated {arguments.transmission_format} transmission of', end=' ',
              file=sys.stderr)
    else:
        print(f'\n\n{arguments.transmission_format.capitalize()} transmission of', end=' ',
              file=sys.stderr)
    print(f'{source_file}', end=' ',
          file=sys.stderr)
    if arguments.port is not None:
        print(f'to {arguments.port}', end=' ',
              file=sys.stderr)
    print(f'completed in {round(stop_time - start_time, 3)} seconds.',
          file=sys.stderr)
    print(f'\tFile format: {"text" if FormatSpecification.TEXT in formats else "binary"} '
          f'(specified as {"inferred" if arguments.file_format is None else arguments.file_format})',
          file=sys.stderr)
    print(f'\tFile size:         {str(statistics[Statistics.FILE_BYTES]).rjust(9)}',
          file=sys.stderr)
    print(f'\tTransmission size: {str(statistics[Statistics.TRANSMITTED_BYTES]).rjust(9)}',
          file=sys.stderr)
    if FormatSpecification.TEXT in formats:
        print(f'\tInitial CP/M  line terminations: {str(statistics[Statistics.INITIAL_CRLF_COUNT]).rjust(6)}',
              file=sys.stderr)
        print(f'\tInitial Apple line terminations: {str(statistics[Statistics.INITIAL_CR_COUNT]).rjust(6)}',
              file=sys.stderr)
        print(f'\tInitial Unix  line terminations: {str(statistics[Statistics.INITIAL_LF_COUNT]).rjust(6)}',
              file=sys.stderr)
        print(f'\tFinal   CP/M  line terminations: {str(statistics[Statistics.FINAL_LINE_TERMINATION_COUNT]).rjust(6)}',
              file=sys.stderr)


if __name__ == '__main__':
    main()
