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
import random
import sys
from enum import Enum, StrEnum
from time import sleep, time
from typing import Dict, FrozenSet, Iterable, List, NamedTuple, Optional, Union

import serial  # from the pyserial package (https://pyserial.readthedocs.io/)


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


class NewlineValue(NamedTuple):
    name: str
    strings: Dict[TransmissionFormat, str]


class Newline(Enum):
    CRLF = NewlineValue(name='CRLF', strings={TransmissionFormat.PLAINTEXT: '\r\n', TransmissionFormat.PACKAGE: '0D0A'})
    LFCR = NewlineValue(name='LFCR', strings={TransmissionFormat.PLAINTEXT: '\n\r', TransmissionFormat.PACKAGE: '0A0D'})
    CR = NewlineValue(name='CR', strings={TransmissionFormat.PLAINTEXT: '\r', TransmissionFormat.PACKAGE: '0D'})
    LF = NewlineValue(name='LF', strings={TransmissionFormat.PLAINTEXT: '\n', TransmissionFormat.PACKAGE: '0A'})


class Arguments(NamedTuple):
    files: List[File]
    serial_port: Optional[Port]
    ms_delay: int
    transmission_format: TransmissionFormat
    source_newlines: FrozenSet[Newline]
    target_newline: Newline
    user_number: int
    echo_transmission: bool
    receive: bool


class Statistics(StrEnum):
    FILE_BYTES = 'file bytes'
    TRANSMITTED_BYTES = 'transmitted bytes'
    PADDING_BYTES = 'padding bytes'
    INITIAL_CRLF_COUNT = f'{Newline.CRLF.value.name} count'
    INITIAL_LFCR_COUNT = f'{Newline.LFCR.value.name} count'
    INITIAL_CR_COUNT = f'{Newline.CR.value.name} count'
    INITIAL_LF_COUNT = f'{Newline.LF.value.name} count'
    FINAL_NEWLINE_COUNT = 'newlines'


statistics: Dict[str, Union[bool, int]] = {
    Statistics.FILE_BYTES: 0,
    Statistics.TRANSMITTED_BYTES: 0,
    Statistics.PADDING_BYTES: 0,
    Statistics.INITIAL_CRLF_COUNT: 0,
    Statistics.INITIAL_LFCR_COUNT: 0,
    Statistics.INITIAL_CR_COUNT: 0,
    Statistics.INITIAL_LF_COUNT: 0,
    Statistics.FINAL_NEWLINE_COUNT: 0,
}


def convert_newlines(string: str, transmission_format: TransmissionFormat,
                     source_newlines: Iterable[Newline], target_newline: Newline) -> str:
    assert transmission_format in {TransmissionFormat.PACKAGE, TransmissionFormat.PLAINTEXT}
    global statistics
    if not hasattr(convert_newlines, 'last_successful_temporary_newline'):
        convert_newlines.last_successful_temporary_newline = '\u0081'  # used only if we can't use '\r' or '\n'
    temporary_newline: str = convert_newlines.last_successful_temporary_newline
    if Newline.LF in source_newlines or '\n' not in string:
        temporary_newline = '\n'
    elif Newline.CR in source_newlines or '\r' not in string:
        temporary_newline = '\r'
    else:
        while temporary_newline in string:
            temporary_newline = chr(random.randint(0x80, 0x100000))
        convert_newlines.last_successful_temporary_newline = temporary_newline
    cr: str = Newline.CR.value.strings[transmission_format]
    lf: str = Newline.LF.value.strings[transmission_format]
    crlf: str = Newline.CRLF.value.strings[transmission_format]
    lfcr: str = Newline.LFCR.value.strings[transmission_format]
    final_newline: str = target_newline.value.strings[transmission_format]
    statistics[Statistics.INITIAL_CRLF_COUNT] += string.count(crlf)
    statistics[Statistics.INITIAL_LFCR_COUNT] += string.count(lfcr)
    statistics[Statistics.INITIAL_CR_COUNT] += (string.count(cr)
                                                - statistics[Statistics.INITIAL_CRLF_COUNT]
                                                - statistics[Statistics.INITIAL_LFCR_COUNT])
    statistics[Statistics.INITIAL_LF_COUNT] += (string.count(lf)
                                                - statistics[Statistics.INITIAL_CRLF_COUNT]
                                                - statistics[Statistics.INITIAL_LFCR_COUNT])
    # convert CP/M, MS-DOS, Windows, etc
    if Newline.CRLF in source_newlines:
        string = string.replace(crlf, temporary_newline)
    # convert BBC Micro
    if Newline.LFCR in source_newlines:
        string = string.replace(lfcr, temporary_newline)
    # convert Apple, Commodore, etc
    if Newline.CR in source_newlines:
        string = string.replace(cr, temporary_newline)
    # convert Unix
    if Newline.LF in source_newlines:
        string = string.replace(lf, temporary_newline)
    string = string.replace(temporary_newline, final_newline)
    statistics[Statistics.FINAL_NEWLINE_COUNT] += string.count(final_newline)
    return string


def echo_character(character: str,
                   file_format: Optional[FileFormat],
                   transmission_format: Optional[TransmissionFormat]) -> None:
    if not hasattr(echo_character, 'first_nibble'):
        echo_character.first_nibble = None
    if not hasattr(echo_character, 'hextet_index'):
        echo_character.hextet_index = 0
    if character == '\\':
        print('\\\\', end='', flush=True)
    elif character == '\t':
        print('\\t', end='\t', flush=True)
    elif character == '\r':
        print('\\r', end='', flush=True)
    elif character == '\n':
        print('\\n', end='\n', flush=True)
    elif transmission_format == TransmissionFormat.PACKAGE:
        if echo_character.first_nibble is None:
            echo_character.first_nibble = character
            print(echo_character.first_nibble, end='', flush=True)
        else:
            second_nibble = character
            echo_character.hextet_index = (echo_character.hextet_index + 1) % 16
            print(character, end=' ', flush=True)
            if file_format == FileFormat.TEXT and echo_character.first_nibble + second_nibble == '0A':
                print('', flush=True)
            if file_format == FileFormat.BINARY and echo_character.hextet_index == 8:
                print('  ', end='', flush=True)
            if file_format == FileFormat.BINARY and echo_character.hextet_index == 0:
                print('', flush=True)
            echo_character.first_nibble = None
    else:
        print(character, end='', flush=True)


def send_string(string: str, destination: Optional[serial.Serial], ms_delay: int, echo_transmission: bool,
                file_format: Optional[FileFormat] = None, transmission_format: Optional[TransmissionFormat] = None) -> None:
    global statistics
    statistics[Statistics.TRANSMITTED_BYTES] += len(string)  # we are assuming 1 byte per character
    for character in string:
        if echo_transmission:
            echo_character(character, file_format, transmission_format)
        if destination is not None:
            destination.write(character.encode())
            destination.flush()
        sleep(ms_delay / 1000.0)


def send_file(original_file: str, target_file: str, destination: Optional[serial.Serial],
              file_format: FileFormat, transmission_format: TransmissionFormat, ms_delay: int, user_number: int,
              source_newlines: Iterable[Newline], target_newline: Newline, echo_transmission: bool) -> None:
    global statistics
    try:
        if transmission_format == TransmissionFormat.PLAINTEXT:
            with open(original_file, 'rt') as source:
                for line in source.readlines():
                    statistics[Statistics.FILE_BYTES] += len(line)  # we are assuming 1 byte per character
                    line = convert_newlines(line, transmission_format, source_newlines, target_newline)
                    send_string(line, destination, ms_delay, echo_transmission, file_format, transmission_format)
        elif transmission_format == TransmissionFormat.PACKAGE:
            with open(original_file, 'rb') as source:
                send_string(f'A:DOWNLOAD {target_file}\r\nU{user_number}\r\n:', destination, ms_delay, echo_transmission)
                byte_count: int = 0
                byte_sum: int = 0
                block_bytes: bytes = source.read(128)
                while block_bytes:
                    statistics[Statistics.FILE_BYTES] += len(block_bytes)
                    block_string: str = ''.join(f'{byte:02x}'.upper() for byte in block_bytes)
                    if file_format == FileFormat.TEXT:
                        block_string = convert_newlines(block_string, transmission_format, source_newlines, target_newline)
                    byte_count += len(block_string) // 2
                    byte_sum += functools.reduce(lambda a, b: a + b,
                                                 [int(block_string[i:i + 2], 16) for i in range(0, len(block_string), 2)])
                    send_string(block_string, destination, ms_delay, echo_transmission, file_format, transmission_format)
                    block_bytes = source.read(128)
                padding_needed: int = 128 - (byte_count % 128)
                statistics[Statistics.PADDING_BYTES] += padding_needed
                if padding_needed > 0:
                    byte_count += padding_needed
                    send_string(''.join('00' for _ in range(padding_needed)),
                                destination, ms_delay, echo_transmission, file_format, transmission_format)
                send_string(f'>{(byte_count & 0xFF):02x}{(byte_sum & 0xFF):02x}'.upper(), destination, ms_delay, echo_transmission)
        else:
            raise ValueError(f'No supported transmission format found in {transmission_format}.')
    except FileNotFoundError:
        print(f'File {original_file} not found.')


def send_files(arguments: Arguments, destination: Optional[serial.Serial]) -> None:
    interfile_delay: float = 1.0
    file_count: int = len(arguments.files)
    for file_number, file in enumerate(arguments.files):
        if file_number > 0:
            sleep(interfile_delay)
        print(f'Uploading file {file_number + 1}/{file_count}: {file.original_path} -> {file.target_name}', flush=True)
        start_time = time()
        send_file(original_file=file.original_path,
                  target_file=file.target_name,
                  destination=destination,
                  file_format=file.format,
                  transmission_format=arguments.transmission_format,
                  ms_delay=arguments.ms_delay,
                  echo_transmission=arguments.echo_transmission,
                  source_newlines=arguments.source_newlines,
                  target_newline=arguments.target_newline,
                  user_number=arguments.user_number)
        stop_time = time()
        sys.stdout.flush()
        if arguments.serial_port is None:
            print(f'\nSimulated {arguments.transmission_format} transmission of', end=' ',
                  file=sys.stderr)
        else:
            print(f'\n\n{arguments.transmission_format.capitalize()} transmission of', end=' ',
                  file=sys.stderr)
        print(f'{file.target_name}', end=' ',
              file=sys.stderr)
        if arguments.serial_port is not None:
            print(f'to {arguments.serial_port.name}', end=' ',
                  file=sys.stderr)
        print(f'completed in {round(stop_time - start_time, 3)} seconds.',
              file=sys.stderr)
        print(f'\tFile format: {file.format} '
              f'(specified as {"inferred" if file.format_inferred else file.format})',
              file=sys.stderr)
        print(f'\tFile size:         {str(statistics[Statistics.FILE_BYTES]).rjust(10)}',
              file=sys.stderr)
        if arguments.transmission_format == TransmissionFormat.PACKAGE:
            print(f'\tBytes of padding:  {str(statistics[Statistics.PADDING_BYTES]).rjust(10)}',
                  file=sys.stderr)
        print(f'\tTransmission size: {str(statistics[Statistics.TRANSMITTED_BYTES]).rjust(10)}',
              file=sys.stderr)
        if file.format == FileFormat.TEXT:
            print(f'\tInitial CRLF newlines: {str(statistics[Statistics.INITIAL_CRLF_COUNT]).rjust(6)}',
                  file=sys.stderr)
            print(f'\tInitial LFCR newlines: {str(statistics[Statistics.INITIAL_LFCR_COUNT]).rjust(6)}',
                  file=sys.stderr)
            print(f'\tInitial CR   newlines: {str(statistics[Statistics.INITIAL_CR_COUNT]).rjust(6)}',
                  file=sys.stderr)
            print(f'\tInitial LF   newlines: {str(statistics[Statistics.INITIAL_LF_COUNT]).rjust(6)}',
                  file=sys.stderr)
            print(f'\tFinal   {arguments.target_newline.value.name.ljust(4)} newlines: {str(statistics[Statistics.FINAL_NEWLINE_COUNT]).rjust(6)}',
                  file=sys.stderr)
        print('', file=sys.stderr)


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
            if len(user_filename_tokens) == 0 or user_filename_tokens[0] == '':
                new_filename = proposed_filename
            elif (1 <= len(user_filename_tokens) <= 2
                  and len(user_filename_tokens[0]) <= 8
                  and len(user_filename_tokens[1]) <= 3):
                new_filename = '.'.join(user_filename_tokens).upper()
            else:
                print(f'{'.'.join(user_filename_tokens).upper()} is not a valid filename.')
    return new_filename


def get_file_format(filename: str, file_format: Optional[str], transmission_format: TransmissionFormat) -> FileFormat:
    binary_file_extensions = {'.BIN', '.COM', '.O'}
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
                # TODO: what will this do with "extended ASCII" (such as 'latin1')? ('utf-8' probably won't help)
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
                                 help='(placeholder--currently unused)\nIndicates that the file transfer will be to receive a file or files from the remote computer (default: the file transfer will be to send a file or files to the remote computer).')
    argument_parser.add_argument('--echo', action=argparse.BooleanOptionalAction, default=True,
                                 help='Cause the transmission to be echoed (or not) to the console (default: echo).')
    argument_parser.add_argument('--source-newlines', type=str, nargs='*',
                                 choices=['CR', 'LF', 'CRLF', 'LFCR', 'system'], default=['system'],
                                 help='One or more types of newlines to be converted to the destination computer\'s newline (default: %(default)s). '
                                      'An empty set of source-newlines indicates that no newline conversion should take place. '
                                      'When sending a file, \'system\' is the host computer\'s newline; when receiving a file, \'system\' is equivalent to CRLF (under the assumption that the remote computer runs CP/M). '
                                      'This option is applicable only to text files and is ignored for binary files.')
    argument_parser.add_argument('--target-newline', type=str, choices=['CR', 'LF', 'CRLF', 'LFCR', 'system'],
                                 default='system',
                                 help='The newline that the source-newlines will be converted to (default: %(default)s). '
                                      'When receiving a file, \'system\' is the host computer\'s newline; when sending a file, \'system\' is equivalent to CRLF (under the assumption that the remote computer runs CP/M). '
                                      'This option is applicable only to text files and is ignored for binary files.'
                                      'This option is ignored if the source-newlines is an empty set.')
    arguments = argument_parser.parse_args()
    # noinspection PyTypeChecker
    transmission_format: TransmissionFormat = TransmissionFormat[arguments.transmission_format.upper()]     # I'm pretty sure the reported type mismatch is a PyCharm problem because the debugger says it's the right type
    local_system_newline: Newline = {'\r\n': Newline.CRLF, '\n\r': Newline.LFCR, '\r': Newline.CR, '\n': Newline.LF}.get(os.linesep)    # TODO: use only for sending; when receiving, simply use '\n'
    remote_system_newline: Newline = Newline.CRLF
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
        # TODO: these are correct only for sending -- swap local/remote_system_newline when receiving
        source_newlines=frozenset(local_system_newline if newline == 'system' else Newline[newline] for newline in arguments.source_newlines),
        target_newline=remote_system_newline if arguments.target_newline == 'system' else Newline[arguments.target_newline],
        user_number=arguments.user,
        echo_transmission=arguments.echo,
        receive=arguments.receive
    )


def main():
    global statistics
    arguments = get_arguments()
    if arguments.serial_port is not None:
        try:
            with serial.Serial(port=arguments.serial_port.name,
                               baudrate=arguments.serial_port.baud_rate,
                               rtscts=arguments.serial_port.flow_control_enabled,
                               exclusive=arguments.serial_port.exclusive_port_access_mode,
                               timeout=1) as destination:
                send_files(arguments, destination)
        except serial.SerialException as e:
            print(f'Failed to write to {arguments.serial_port.name}: {e}')
            exit(1)
    else:
        send_files(arguments, None)


if __name__ == '__main__':
    main()
