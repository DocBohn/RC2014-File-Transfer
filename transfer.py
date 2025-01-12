"""
@file transfer.py
@license MIT License
@copyright (c) 2025 Christopher A. Bohn
@author Christopher A. Bohn

@brief Python program to upload files to, and download files from, an RC2014 (or similar retrocomputers)

This program can transmit text files as plaintext (no special encoding), or it
can package text or binary files to a CP/M computer that has [Grant Searle's
`DOWNLOAD.COM`](http://searle.x10host.com/cpm/index.html) on its A: drive.

This program can receive a text file as plaintext (no special encoding), or it
can receive packaged text or binary files from a CP/M computer that has
[Sheila](https://blog.peacockmedia.software/2022/01/uploadcom-for-z80-cpm-writing-utility.html)
[Dixon's](https://blog.peacockmedia.software/2022/01/uploadcom-for-z80-cpm-usage.html)
[`UPLOAD.COM`](https://github.com/RC2014Z80/RC2014/blob/master/CPM/UPLOAD.COM/README.md) on its A: drive.

The nominal use is with one of [Spencer Owen's RC2014 computers](https://rc2014.co.uk/)
or a [similar retrocomputer](https://smallcomputercentral.com/).

There are a handful of options; however, a typical transmission (115.2 kilobaud,
file packaged for `DOWNLOAD.COM`) can be achieved by specifying only the port
(with the `-p` option) and the file to be uploaded.

TODO: should we provide an option to convert spaces to tabs, and/or vice-versa?
      also: tabs being converted to spaces during reception is probably only a problem for plaintext
TODO: work with SCM
TODO: what if UPLOAD.COM isn't there?
TODO: handle remote computer not powered up, or not yet booted into CP/M, etc
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
import glob
import io
import os
import random
import re
import sys
from enum import Enum, StrEnum
from time import sleep, time
from typing import Dict, FrozenSet, Iterable, List, NamedTuple, Optional, Set, Union

import pyperclip  # from the pyperclip package (https://pyperclip.readthedocs.io/)
import serial  # from the pyserial package  (https://pyserial.readthedocs.io/)


class TransmissionFormat(StrEnum):
    PACKAGE = 'package'
    CPM_PLAINTEXT = 'cpm-plaintext'
    BASIC_PLAINTEXT = 'basic-plaintext'


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
    CRLF = NewlineValue(name='CRLF', strings={TransmissionFormat.BASIC_PLAINTEXT: '\r\n',
                                              TransmissionFormat.CPM_PLAINTEXT: '\r\n',
                                              TransmissionFormat.PACKAGE: '0D0A'})
    LFCR = NewlineValue(name='LFCR', strings={TransmissionFormat.BASIC_PLAINTEXT: '\n\r',
                                              TransmissionFormat.CPM_PLAINTEXT: '\n\r',
                                              TransmissionFormat.PACKAGE: '0A0D'})
    CR = NewlineValue(name='CR', strings={TransmissionFormat.BASIC_PLAINTEXT: '\r',
                                          TransmissionFormat.CPM_PLAINTEXT: '\r',
                                          TransmissionFormat.PACKAGE: '0D'})
    LF = NewlineValue(name='LF', strings={TransmissionFormat.BASIC_PLAINTEXT: '\n',
                                          TransmissionFormat.CPM_PLAINTEXT: '\n',
                                          TransmissionFormat.PACKAGE: '0A'})


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


CHARACTER_ENCODING: str = 'ascii'
PADDING_CHARACTERS: FrozenSet[str] = frozenset({'\0', '\x1A'})  # NUL used by rc2014.co.uk packager; SUB used by ED.COM
PREFERRED_PADDING: str = '\0'
PREFERRED_PADDING_HEX: str = '\0'
SERIAL_TIMEOUT_MS: int = 250
INTERFILE_DELAY_MS: int = 1000
DEBUG_REMOTE_RESPONSES: bool = False


def convert_newlines(string: str,
                     transmission_format: TransmissionFormat,
                     source_newlines: Iterable[Newline],
                     target_newline: Newline) -> str:
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
    return string


def echo_character(character: str,
                   file_format: Optional[FileFormat],
                   transmission_format: Optional[TransmissionFormat] = None) -> None:
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
    elif character == '\0':
        print('\\0', end='', flush=True)
    elif character == '\x1A':
        print('\\x1A', end='', flush=True)
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


def send_string(string: str,
                destination: Optional[Union[io.BytesIO, serial.Serial]],
                ms_delay: int,
                echo_transmission: bool,
                file_format: Optional[FileFormat] = None,
                transmission_format: Optional[TransmissionFormat] = None) -> None:
    for character in string:
        if echo_transmission:
            echo_character(character, file_format, transmission_format)
        if destination is not None:
            destination.write(character.encode())
            destination.flush()
        sleep(ms_delay / 1000.0)


def flush_receive_buffer(source: Optional[Union[io.BytesIO, serial.Serial]], termination_byte: bytes = b'') -> str:
    if source is None:
        return ''
    print('[[', end='', flush=True)
    buffer: io.StringIO = io.StringIO()
    message: bytes = source.read(1)
    while message != termination_byte:
        buffer.write(message.decode(CHARACTER_ENCODING))
        if DEBUG_REMOTE_RESPONSES:
            echo_character(message.decode(CHARACTER_ENCODING), FileFormat.TEXT)
        else:
            print('.', end='', flush=True)
        message = source.read(1)
    print(']]', flush=True)
    buffer.seek(0)
    return buffer.read()


def send_cpm_command(command: str,
                     destination: serial.Serial,
                     ms_delay: int,
                     echo_transmission: bool,
                     flush_all_lines: bool = True) -> str:
    send_string(command, destination, ms_delay, echo_transmission)
    return flush_receive_buffer(destination, b'' if flush_all_lines else b'\n')


def receive_plaintext(source: Optional[Union[io.BytesIO, serial.Serial]],
                      buffer: io.StringIO,
                      message: bytes,
                      echo_transmission: bool) -> str:
    while message != b'':
        message = source.read(1)
        buffer.write(message.decode(CHARACTER_ENCODING))
        if echo_transmission:
            echo_character(message.decode(CHARACTER_ENCODING), FileFormat.TEXT)
    print()
    buffer.seek(0)
    return buffer.read()


def receive_basic_plaintext_file(target_file: str,
                                 source: Optional[Union[io.BytesIO, serial.Serial]],
                                 ms_delay: int,
                                 source_newlines: Iterable[Newline],
                                 target_newline: Newline,
                                 echo_transmission: bool) -> None:
    message: bytes = b'ignored'
    buffer: io.StringIO = io.StringIO()
    if source is None:
        send_string(f'LIST\n', source, ms_delay, echo_transmission)
        return
    elif isinstance(source, io.BytesIO):
        source.write(pyperclip.paste().encode(CHARACTER_ENCODING))
        source.seek(0)
    else:   # this only works if we use '\r\n' instead of '\n' (cf., receive_cpm_plaintext_file)
        send_string(f'LIST\r\n', source, ms_delay, echo_transmission)
        message = source.readline()
        if echo_transmission:
            for character in message.decode(CHARACTER_ENCODING):
                echo_character(character, FileFormat.TEXT)
    file_contents: str = receive_plaintext(source, buffer, message, echo_transmission)
    bbc_basic_termination: str = '>'
    ms_basic_termination: str = 'Ok\r\n'
    match file_contents:
        case s if s.endswith(bbc_basic_termination):
            file_contents = s[:-len(bbc_basic_termination)]
        case s if s.endswith(ms_basic_termination):
            file_contents = s[:-len(ms_basic_termination)]
        case _:
            pass
    with open(target_file, 'wt') as file:
        file.write(convert_newlines(file_contents, TransmissionFormat.BASIC_PLAINTEXT, source_newlines, target_newline))


def receive_cpm_plaintext_file(original_file: str,
                               target_file: str,
                               source: Optional[Union[io.BytesIO, serial.Serial]],
                               ms_delay: int,
                               user_number: int,
                               source_newlines: Iterable[Newline],
                               target_newline: Newline,
                               echo_transmission: bool) -> None:
    message: bytes = b'ignored'
    file_contents: str
    if source is None:
        # send_string(f'USER {user_number}\n', source, ms_delay, echo_transmission)
        send_string(f'TYPE {original_file}\n', source, ms_delay, echo_transmission)
        return
    elif isinstance(source, io.BytesIO):
        source.write(pyperclip.paste().encode(CHARACTER_ENCODING))
        source.seek(0)
    else:   # this only works if we use '\n' instead of '\r\n' (cf., receive_basic_plaintext_file)
        # send_cpm_command(f'USER {user_number}\n', source, ms_delay, echo_transmission)
        send_cpm_command(f'TYPE {original_file}\n', source, ms_delay, echo_transmission, False)
    file_contents: str = receive_plaintext(source, io.StringIO(), message, echo_transmission)
    if not isinstance(source, serial.Serial):
        file_contents += 'X>' if file_contents[-1] == '\n' else '\nX>'
    # the command line prompt should be at the end of the buffer
    assert (file_contents[-1] == '>' and file_contents[-2].isupper())
    end_of_file: int = -2
    # I suspect there's a '\r\n' between the padding characters and the command line prompt, but we'll consider the possibility that's not the case
    if file_contents[-3] in PADDING_CHARACTERS:
        end_of_file = -3
    if file_contents[-4] in PADDING_CHARACTERS:
        end_of_file = -4
    if file_contents[-5] in PADDING_CHARACTERS:
        end_of_file = -5
    while file_contents[end_of_file - 1] in PADDING_CHARACTERS:
        end_of_file -= 1
    if file_contents[:end_of_file].endswith('\r\n\r\n'):
        end_of_file -= 2
    with open(target_file, 'wt') as file:
        file.write(convert_newlines(file_contents[:end_of_file], TransmissionFormat.CPM_PLAINTEXT, source_newlines, target_newline))


def receive_package_file(original_file: str,
                         target_file: str,
                         source: Optional[Union[io.BytesIO, serial.Serial]],
                         file_format: FileFormat,
                         ms_delay: int,
                         user_number: int,
                         source_newlines: Iterable[Newline],
                         target_newline: Newline,
                         echo_transmission: bool) -> None:
    message: bytes = b'ignored'
    buffer: io.StringIO = io.StringIO()
    if source is None:
        # send_string(f'USER {user_number}\n', source, ms_delay, echo_transmission)
        send_string(f'A:UPLOAD {original_file}\n', source, ms_delay, echo_transmission)
        return
    elif isinstance(source, io.BytesIO):
        source.write(pyperclip.paste().encode(CHARACTER_ENCODING))
        source.seek(0)
        message = source.read(1)
    else:   # this only with both '\n' and 'r\n' (cf., receive_cpm_plaintext_file)
        # send_cpm_command(f'USER {user_number}\n', source, ms_delay, echo_transmission)
        send_string(f'A:UPLOAD {original_file}\n', source, ms_delay, echo_transmission)
        print('[[', end='', flush=True)
        # Read the first line of the response (echo of the command)
        while message != b'\n':
            message = source.read(1)
            if DEBUG_REMOTE_RESPONSES:
                echo_character(message.decode(CHARACTER_ENCODING), FileFormat.TEXT)
            else:
                print('.', end='', flush=True)
        # Work our way through one or two newlines (including the '\n' we just consumed)
        while message in {b'\r', b'\n'}:
            if DEBUG_REMOTE_RESPONSES:
                echo_character(message.decode(CHARACTER_ENCODING), FileFormat.TEXT)
            else:
                print('.', end='', flush=True)
            message = source.read(1)
        print(']]', flush=True)
    # Is it "Can't find input file$", "Break key pressed$", or "A: DOWNLOAD $"? *OR* are we already at the delimiter?
    if message != b'A' and message != b':':
        print(f'Response: {message.decode(CHARACTER_ENCODING)}'
              f'{receive_plaintext(source, buffer, message, False).splitlines()[0]}', flush=True)
    else:
        # 'A'
        if echo_transmission:
            echo_character(message.decode(CHARACTER_ENCODING), FileFormat.TEXT)
        message = source.read(1)    # ':'
        if echo_transmission:
            echo_character(message.decode(CHARACTER_ENCODING), FileFormat.TEXT)
        message = source.read(1)    # 'D'
        # Get to the initial delimiter
        while message != b':':
            if echo_transmission:
                echo_character(message.decode(CHARACTER_ENCODING), FileFormat.TEXT)
            message = source.read(1)
        if echo_transmission:
            echo_character(message.decode(CHARACTER_ENCODING), FileFormat.TEXT)
        print()
        # We are now at the data -- get to the terminal delimiter
        message = source.read(1)
        while message != b'>':
            buffer.write(message.decode(CHARACTER_ENCODING))
            if echo_transmission:
                echo_character(message.decode(CHARACTER_ENCODING), file_format, TransmissionFormat.PACKAGE)
            message = source.read(1)
        length: int = int(source.read(2).decode(CHARACTER_ENCODING), 16)
        checksum: int = int(source.read(2).decode(CHARACTER_ENCODING), 16)
        print(f'>{length:02X}{checksum:02X}', flush=True)
        # Save the data
        buffer.seek(0)
        file_contents: str = buffer.read()
        file_bytes: List[int] = [int(file_contents[i:i+2], 16) for i in range(0, len(file_contents), 2)]
        byte_count: int = len(file_bytes) & 0xFF
        byte_sum: int = sum(file_bytes) & 0xFF
        if length != byte_count:
            print(f'Length error! Package reports {length:02X}; Found {byte_count:02X}')
        elif checksum != byte_sum:
            print(f'Checksum error! Package reports {checksum:02X}; Found {byte_sum:02X}')
        else:
            if file_format == FileFormat.TEXT:
                file_characters: str = convert_newlines(''.join(chr(byte) for byte in file_bytes),
                                                        TransmissionFormat.CPM_PLAINTEXT, source_newlines, target_newline)
                end_of_file: int = 0
                while file_characters[end_of_file - 1] in PADDING_CHARACTERS:
                    end_of_file -= 1
                with open(target_file, 'wt') as file:
                    file.write(file_characters if end_of_file == 0 else file_characters[:end_of_file])
            else:
                with open(target_file, 'wb') as file:
                    for byte in file_bytes:
                        file.write(byte.to_bytes(1, byteorder=sys.byteorder))
    flush_receive_buffer(source)


def send_basic_plaintext_file(original_file: str,
                              destination: Optional[Union[io.BytesIO, serial.Serial]],
                              ms_delay: int,
                              source_newlines: Iterable[Newline],
                              target_newline: Newline,
                              echo_transmission: bool) -> None:
    with open(original_file, 'rt') as source:
        for line in source.readlines():
            line = convert_newlines(line, TransmissionFormat.BASIC_PLAINTEXT, source_newlines, target_newline)
            send_string(line, destination, ms_delay, echo_transmission, FileFormat.TEXT, TransmissionFormat.BASIC_PLAINTEXT)


def send_cpm_plaintext_file(original_file: str,
                            target_file: str,
                            destination: Optional[Union[io.BytesIO, serial.Serial]],
                            ms_delay: int,
                            user_number: int,
                            source_newlines: Iterable[Newline],
                            target_newline: Newline,
                            echo_transmission: bool) -> None:
    with open(original_file, 'rt') as source:
        send_cpm_command(f'USER {user_number}\n', destination, ms_delay, echo_transmission)
        # remove the original, if it exists
        send_cpm_command(f'ERA {target_file}\n', destination, ms_delay, echo_transmission)
        send_cpm_command(f'C:ED {target_file.upper()}\n', destination, ms_delay, echo_transmission)
        # capital-I seems to force all-uppercase; lowercase-I seems to preserve the case
        send_string('i\n', destination, ms_delay, echo_transmission)
        for line in source.readlines():
            # ED.COM seems to convert '\r' to '\r\n', so '\r\n' becomes '\r\n\n' (cf., receive_basic/cpm_plaintext_file)
            line = convert_newlines(line, TransmissionFormat.CPM_PLAINTEXT, source_newlines, Newline.CR)
            send_string(line, destination, ms_delay, echo_transmission, FileFormat.TEXT, TransmissionFormat.CPM_PLAINTEXT)
        send_string('\x1AE\n\n', destination, ms_delay, echo_transmission)
        flush_receive_buffer(destination)
        # erase the empty backup file
        send_cpm_command(f'ERA {target_file.split('.')[0]}.BAK\n', destination, ms_delay, echo_transmission)


def send_package_file(original_file: str,
                      target_file: str,
                      destination: Optional[Union[io.BytesIO, serial.Serial]],
                      file_format: FileFormat,
                      ms_delay: int,
                      user_number: int,
                      source_newlines: Iterable[Newline],
                      target_newline: Newline,
                      echo_transmission: bool) -> None:
    with open(original_file, 'rb') as source:
        send_string(f'A:DOWNLOAD {target_file}\nU{user_number}\n:', destination, ms_delay, echo_transmission)
        byte_count: int = 0
        byte_sum: int = 0
        block_bytes: bytes = source.read(128)
        while block_bytes:
            block_string: str = ''.join(f'{byte:02X}' for byte in block_bytes)
            if file_format == FileFormat.TEXT:
                block_string = convert_newlines(block_string, TransmissionFormat.PACKAGE, source_newlines, target_newline)
            byte_count += len(block_string) // 2
            byte_sum += functools.reduce(lambda a, b: a + b,
                                         [int(block_string[i:i + 2], 16) for i in range(0, len(block_string), 2)])
            send_string(block_string, destination, ms_delay, echo_transmission, file_format, TransmissionFormat.PACKAGE)
            block_bytes = source.read(128)
        # if we need an end of file marker, we need at least one SUB character
        padding_needed: int = 128 - (byte_count % 128)
        # but if this CP/M version is happy with file length as a multiple of 128, no marker is needed
        if PREFERRED_PADDING == '\0' and padding_needed == 128:
            padding_needed = 0
        byte_count += padding_needed
        byte_sum += padding_needed * ord(PREFERRED_PADDING)
        send_string(''.join(f'{ord(PREFERRED_PADDING):02X}' for _ in range(padding_needed)),
                    destination, ms_delay, echo_transmission, file_format, TransmissionFormat.PACKAGE)
        send_string(f'>{(byte_count & 0xFF):02X}{(byte_sum & 0xFF):02X}', destination, ms_delay, echo_transmission)
        if destination is not None:
            remote_computer_response: str = receive_plaintext(destination, io.StringIO(), b'ignored', False)
            if DEBUG_REMOTE_RESPONSES:
                print('[[')
                print(remote_computer_response)
                print(']]', flush=True)
            elif isinstance(destination, serial.Serial):
                print(f'Response: {' '.join(remote_computer_response.splitlines())}', flush=True)


def receive_files(arguments: Arguments,
                  source: Optional[Union[io.BytesIO, serial.Serial]]) -> None:
    file_count: int = len(arguments.files)
    for file_number, file in enumerate(arguments.files):
        if file_number > 0:
            sleep(INTERFILE_DELAY_MS / 1000.0)
        print(f'\nDownloading file {file_number + 1}/{file_count}: '
              f'{"BASIC Interpreter" if arguments.transmission_format == TransmissionFormat.BASIC_PLAINTEXT else file.original_path}'
              f' -> {file.target_name}',
              flush=True)
        start_time: float = time()
        match arguments.transmission_format:
            case TransmissionFormat.BASIC_PLAINTEXT:
                receive_basic_plaintext_file(target_file=file.target_name,
                                             source=source,
                                             ms_delay=arguments.ms_delay,
                                             source_newlines=arguments.source_newlines,
                                             target_newline=arguments.target_newline,
                                             echo_transmission=arguments.echo_transmission)
            case TransmissionFormat.CPM_PLAINTEXT:
                receive_cpm_plaintext_file(original_file=file.original_path,
                                           target_file=file.target_name,
                                           source=source,
                                           ms_delay=arguments.ms_delay,
                                           user_number=arguments.user_number,
                                           source_newlines=arguments.source_newlines,
                                           target_newline=arguments.target_newline,
                                           echo_transmission=arguments.echo_transmission)
            case TransmissionFormat.PACKAGE:
                receive_package_file(original_file=file.original_path,
                                     target_file=file.target_name,
                                     source=source,
                                     file_format=file.format,
                                     ms_delay=arguments.ms_delay,
                                     user_number=arguments.user_number,
                                     source_newlines=arguments.source_newlines,
                                     target_newline=arguments.target_newline,
                                     echo_transmission=arguments.echo_transmission)
            case _:
                raise ValueError(f'Unknown transmission format: {arguments.transmission_format}')
        stop_time: float = time()
        sys.stdout.flush()
        if arguments.serial_port is None:
            print(f'\nSimulated {arguments.transmission_format} reception of', end=' ')
        else:
            print(f'\n\n{arguments.transmission_format.capitalize()} reception of', end=' ')
        print(f'{file.original_path}', end=' ')
        if arguments.serial_port is not None:
            print(f'from {arguments.serial_port.name}', end=' ')
        print(f'({file_number + 1}/{file_count}) completed in {round(stop_time - start_time, 3)} seconds.'
              f' File format: {file.format} '
              f'(specified as {"inferred" if file.format_inferred else file.format})', flush=True)


def send_files(arguments: Arguments,
               destination: Optional[Union[io.BytesIO, serial.Serial]]) -> None:
    file_count: int = len(arguments.files)
    for file_number, file in enumerate(arguments.files):
        if file_number > 0:
            sleep(INTERFILE_DELAY_MS / 1000.0)
        print(f'\nUploading file {file_number + 1}/{file_count}: {file.original_path} -> '
              f'{"BASIC Interpreter" if arguments.transmission_format == TransmissionFormat.BASIC_PLAINTEXT else file.target_name}',
              flush=True)
        start_time: float = time()
        try:
            match arguments.transmission_format:
                case TransmissionFormat.BASIC_PLAINTEXT:
                    send_basic_plaintext_file(original_file=file.original_path,
                                              destination=destination,
                                              ms_delay=arguments.ms_delay,
                                              echo_transmission=arguments.echo_transmission,
                                              source_newlines=arguments.source_newlines,
                                              target_newline=arguments.target_newline)
                case TransmissionFormat.CPM_PLAINTEXT:
                    send_cpm_plaintext_file(original_file=file.original_path,
                                            target_file=file.target_name,
                                            destination=destination,
                                            ms_delay=arguments.ms_delay,
                                            echo_transmission=arguments.echo_transmission,
                                            source_newlines=arguments.source_newlines,
                                            target_newline=arguments.target_newline,
                                            user_number=arguments.user_number)
                case TransmissionFormat.PACKAGE:
                    send_package_file(original_file=file.original_path,
                                      target_file=file.target_name,
                                      destination=destination,
                                      file_format=file.format,
                                      ms_delay=arguments.ms_delay,
                                      echo_transmission=arguments.echo_transmission,
                                      source_newlines=arguments.source_newlines,
                                      target_newline=arguments.target_newline,
                                      user_number=arguments.user_number)
                case _:
                    raise ValueError(f'Unknown transmission format: {arguments.transmission_format}')
        except FileNotFoundError:
            print(f'File {file.original_path} not found.')
        stop_time: float = time()
        sys.stdout.flush()
        if isinstance(destination, io.BytesIO):
            destination.seek(0)
            pyperclip.copy(destination.read().decode(CHARACTER_ENCODING))
            if not pyperclip.is_available():
                print('\nClipboard is unavailable.')
        if arguments.serial_port is None:
            print(f'\nSimulated {arguments.transmission_format} transmission of', end=' ')
        else:
            print(f'\n\n{arguments.transmission_format.capitalize()} transmission of', end=' ')
        print(f'{file.target_name}', end=' ')
        if arguments.serial_port is not None:
            print(f'to {arguments.serial_port.name}', end=' ')
        print(f'({file_number + 1}/{file_count}) completed in {round(stop_time - start_time, 3)} seconds.'
              f' File format: {file.format} '
              f'(specified as {"inferred" if file.format_inferred else file.format})', flush=True)


def expand_wildcards(filespec: str,
                     remote_connection: Optional[Union[io.BytesIO, serial.Serial]],
                     transmission_format: TransmissionFormat,
                     receiving_file: bool,
                     ms_delay: int,
                     user_number: int,
                     echo_transmission: bool) -> Set[str]:
    # if {'?', '*', '[', ']'}.isdisjoint(filespec):
    #     return {filespec}
    if not receiving_file:
        matching_files = glob.glob(filespec)
        if not matching_files:
            print(f'No file matching "{filespec}"')
        return set(matching_files)
    if (remote_connection is None
            or isinstance(remote_connection, io.BytesIO)
            or transmission_format == TransmissionFormat.BASIC_PLAINTEXT):
        # make something up
        segmented_filespec: List[str] = [segment for segment in re.split(r'(\[[^\]]*\])', filespec) if segment]
        filename: str = ''
        for segment in segmented_filespec:
            if segment[0] == '[':
                filename = filename + segment[1]
            else:
                filename = filename + segment.replace('?', 'A').replace('*', '')
        return {filename}
    send_cpm_command(f'USER {user_number}\n', remote_connection, ms_delay, echo_transmission)
    directory_response: List[str] = send_cpm_command(f'DIR {filespec.upper()}\n',
                                                     remote_connection,
                                                     ms_delay,
                                                     echo_transmission).splitlines()[1:-1]
    if directory_response[-1] == 'No file':
        print('Response: No file', flush=True)
        return set()
    else:
        filenames: Set[str] = set()
        for line in directory_response:
            directory: str = line[0] if len(line) > 0 else ''
            for filename in line.split(':')[1:]:
                filenames.add(f'{directory}:{".".join(filename.split())}')
        return filenames


# TODO: warn if (truncated) filename matches another filename
def truncate_filename(filename: str,
                      receiving_file: bool) -> str:
    new_filename: str = ''
    if receiving_file:
        if len(filename) > 2 and filename[0].isalpha() and filename[1] == ':':
            new_filename = filename[2:]
        else:
            new_filename = filename
    else:
        _, filename = os.path.split(filename)
        name, extension = os.path.splitext(filename)
        name = name.replace('.', '-')
        if len(name) > 8:
            name = name[:8].rstrip('-')
        if len(extension) > 4:
            extension = extension[:4]
        proposed_filename: str = f'{name}{extension}'.upper()
        if proposed_filename == filename.upper():
            new_filename = proposed_filename
        else:
            while new_filename == '':
                user_filename_tokens: List[str]
                user_filename_tokens = (input(f'{filename} needs to be renamed to 8.3 format [{proposed_filename}]: ')
                                        .split('.'))
                if len(user_filename_tokens) == 0 or user_filename_tokens[0] == '':
                    new_filename = proposed_filename
                elif len(user_filename_tokens) == 1 and len(user_filename_tokens[0]) <= 8:
                    new_filename = user_filename_tokens[0].upper()
                elif (len(user_filename_tokens) == 2
                      and len(user_filename_tokens[0]) <= 8
                      and len(user_filename_tokens[1]) <= 3):
                    new_filename = '.'.join(user_filename_tokens).upper()
                else:
                    print(f'{'.'.join(user_filename_tokens).upper()} is not a valid filename.')
    return new_filename


def get_file_format(filename: str,
                    specified_file_format: Optional[FileFormat],
                    transmission_format: TransmissionFormat,
                    receiving_file: bool) -> FileFormat:
    binary_file_extensions = {'.BIN', '.COM', '.O'}
    text_file_extensions = {'.TXT', '.ME',                  # Plain text
                            '.BAK',                         # Backup from text editor
                            '.ASM', '.Z80', '.HEX', '.IHX', # Assembly, Intel Hex
                            '.LIS', '.LST', '.MAP', '.SYM', # Linker & debugger files
                            '.ADB', '.ADS',                 # Ada
                            '.BAS',                         # BASIC
                            '.C', '.H',                     # C
                            '.F', '.F77', '.FOR',           # FORTRAN
                            '.F', '.FTH', '.FS', '.4TH',    # Forth
                            '.PAS',                         # Pascal
                            '.JSON', '.XML'                 # Text-based data files (n.b., '.DAT' might not be text)
                            '.MD', '.TEX',                  # Markup files (including markdown)
                            '.PKG'}                         # We can send packages as "basic-plaintext"
    if transmission_format in {TransmissionFormat.BASIC_PLAINTEXT, TransmissionFormat.CPM_PLAINTEXT}:
        return FileFormat.TEXT
    if specified_file_format is not None:
        return specified_file_format
    if any(filename.upper().endswith(extension.upper()) for extension in text_file_extensions):
        return FileFormat.TEXT
    if any(filename.upper().endswith(extension.upper()) for extension in binary_file_extensions):
        return FileFormat.BINARY
    if receiving_file:
        return FileFormat.BINARY    # The worst that'll happen is that we have '\r\n' when we only need '\n', and there'll be padding characters at the end of the file
    file_format: FileFormat
    try:
        with open(filename, 'rb') as file:
            first_kilobyte: bytes = file.read(1024)
            first_kilobyte.decode(CHARACTER_ENCODING)
            # if the first KB can be decoded as text, then it's probably text
            file_format = FileFormat.TEXT
    except UnicodeDecodeError:
        file_format = FileFormat.BINARY
    except FileNotFoundError:
        # if the file doesn't exist, then the format doesn't matter
        # (the absence of the file is handled elsewhere)
        file_format = FileFormat.BINARY
    return file_format


def populate_file_specs(file: File,
                        filenames: Iterable[str],
                        transmission_format: TransmissionFormat,
                        receiving_file: bool) -> List[File]:
    updated_files: List[File] = []
    for filename in filenames:
        target_name: str = truncate_filename(filename, receiving_file)
        actual_format: FileFormat = get_file_format(target_name,
                                                    file.format,
                                                    transmission_format,
                                                    receiving_file)
        updated_files.append(File(
            original_path=filename,
            target_name=target_name,
            format=actual_format,
            format_inferred=(file.format is None),
            format_overridden=file.format is not None and file.format != actual_format
        ))
    return updated_files


def get_arguments() -> Arguments:
    argument_parser = argparse.ArgumentParser(
        prog='transfer',
        description='Transfer file to/from RC2014 or similar retrocomputer'
    )
    argument_parser.add_argument('source_file', type=str, nargs='+')
    argument_parser.add_argument('-p', '--port', type=str, default=None,
                                 help='The serial port for the serial connection (if omitted, transfer.py will only print to the console, no transmission will be made). '
                                      'If \'clipboard\' is specified, then the encoded file will be copied to/from the clipboard (no the transmission will be made).')
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
                                 help='The delay (in milliseconds) between characters (default: %(default)s). '
                                      'A delay shouldn\'t be necessary if flow control is enabled. '
                                      'Applies only when sending characters to the remote computer.')
    argument_parser.add_argument('-tf', '--transmission-format', choices=['package', 'cpm-plaintext', 'basic-plaintext'], default='package',
                                 help='The transmission format (default: %(default)s).')
    argument_parser.add_argument('-ff', '--file-format', choices=['binary', 'text'], default=None,
                                 help='The file format (default: inferred file type). '
                                      'n.b., if the transmission format is \'cpm-plaintext\' or \'basic-plaintext\', then the file format argument is ignored and replaced with \'text\'.')
    argument_parser.add_argument('-u', '--user', type=int, default=0,
                                 choices=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
                                 help='The CP/M user number (default: %(default)s).')
    argument_parser.add_argument('-rx', '--receive', action='store_true',
                                 help='Indicates that the file transfer will be to receive a file or files from the remote computer (default: the file transfer will be to send a file or files to the remote computer).')
    argument_parser.add_argument('--echo', action=argparse.BooleanOptionalAction, default=True,
                                 help='Cause the transmission to be echoed (or not) to the local computer\'s console (default: echo).')
    argument_parser.add_argument('--source-newlines', type=str, nargs='*',
                                 choices=['CR', 'LF', 'CRLF', 'LFCR', 'system'], default=['system'],
                                 help='Zero or more types of newlines to be converted to the destination computer\'s newline (default: %(default)s). '
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
    # I'm pretty sure the reported type mismatch is a PyCharm problem because the debugger says it's the right type
    # noinspection PyTypeChecker
    transmission_format: TransmissionFormat = TransmissionFormat[arguments.transmission_format.replace('-', '_').upper()]
    # https://docs.python.org/3.12/library/os.html#os.linesep says to use simply '\n' instead of os.linesep when writing files opened in text mode, but it appears as though a serial connection doesn't count
    local_system_newline: Newline = {'\r\n': Newline.CRLF, '\n\r': Newline.LFCR, '\r': Newline.CR, '\n': Newline.LF}.get(os.linesep)
    remote_system_newline: Newline = Newline.CRLF
    source_system_newline: Newline = remote_system_newline if arguments.receive else local_system_newline
    target_system_newline: Newline = local_system_newline if arguments.receive else remote_system_newline
    return Arguments(
        files=[File(original_path=source_file,
                    target_name='',                                                                 # placeholder
                    format=FileFormat(arguments.file_format) if arguments.file_format else None,    # placeholder
                    format_inferred=False,                                                          # placeholder
                    format_overridden=False)                                                        # placeholder
               for source_file in set(arguments.source_file)],
        serial_port=Port(name=arguments.port,
                         flow_control_enabled=arguments.flow_control,
                         exclusive_port_access_mode=arguments.exclusive_port,
                         baud_rate=arguments.baud) if arguments.port is not None else None,
        ms_delay=arguments.delay,
        transmission_format=transmission_format,
        source_newlines=frozenset(source_system_newline if newline == 'system' else Newline[newline] for newline in arguments.source_newlines),
        target_newline=target_system_newline if arguments.target_newline == 'system' else Newline[arguments.target_newline],
        user_number=arguments.user,
        echo_transmission=arguments.echo,
        receive=arguments.receive
    )


def main():
    arguments = get_arguments()
    complete_files: List[File] = []
    if arguments.serial_port is None:
        for file in arguments.files:
            filenames: Set[str] = expand_wildcards(file.original_path,
                                                   None,
                                                   arguments.transmission_format,
                                                   arguments.receive,
                                                   arguments.ms_delay,
                                                   arguments.user_number,
                                                   arguments.echo_transmission)
            complete_files.extend(
                populate_file_specs(file, filenames, arguments.transmission_format, arguments.receive))
        arguments = Arguments(
            files=complete_files,
            serial_port=arguments.serial_port,
            ms_delay=arguments.ms_delay,
            transmission_format=arguments.transmission_format,
            source_newlines=arguments.source_newlines,
            target_newline=arguments.target_newline,
            user_number=arguments.user_number,
            echo_transmission=arguments.echo_transmission,
            receive=arguments.receive
        )
        if arguments.receive:
            receive_files(arguments, None)
        else:
            send_files(arguments, None)
    else:
        try:
            connection: Union[io.BytesIO, serial.Serial] = \
                io.BytesIO() if arguments.serial_port.name.lower() == 'clipboard' \
                    else serial.Serial(port=arguments.serial_port.name,
                                       baudrate=arguments.serial_port.baud_rate,
                                       rtscts=arguments.serial_port.flow_control_enabled,
                                       exclusive=arguments.serial_port.exclusive_port_access_mode,
                                       timeout=SERIAL_TIMEOUT_MS / 1000.0)
            for file in arguments.files:
                filenames: Set[str] = expand_wildcards(file.original_path,
                                                       connection,
                                                       arguments.transmission_format,
                                                       arguments.receive,
                                                       arguments.ms_delay,
                                                       arguments.user_number,
                                                       arguments.echo_transmission)
                complete_files.extend(populate_file_specs(file, filenames, arguments.transmission_format, arguments.receive))
            arguments = Arguments(
                files = complete_files,
                serial_port = arguments.serial_port,
                ms_delay = arguments.ms_delay,
                transmission_format = arguments.transmission_format,
                source_newlines = arguments.source_newlines,
                target_newline = arguments.target_newline,
                user_number = arguments.user_number,
                echo_transmission = arguments.echo_transmission,
                receive = arguments.receive
            )
            if arguments.receive:
                with connection as source:
                    receive_files(arguments, source)
            else:
                with connection as destination:
                    send_files(arguments, destination)
        except serial.SerialException as e:
            print(f'Connection failure on {arguments.serial_port.name}: {e}', file=sys.stderr)
            exit(1)



    # arguments.files = process_filenames(arguments)

    # if arguments.receive:
    #     if arguments.serial_port is None:
    #         receive_files(arguments, None)
    #     elif arguments.serial_port.name.lower() == 'clipboard':
    #         with io.BytesIO() as buffer:
    #             receive_files(arguments, buffer)
    #     else:
    #         try:
    #             with serial.Serial(port=arguments.serial_port.name,
    #                                baudrate=arguments.serial_port.baud_rate,
    #                                rtscts=arguments.serial_port.flow_control_enabled,
    #                                exclusive=arguments.serial_port.exclusive_port_access_mode,
    #                                timeout=SERIAL_TIMEOUT_MS / 1000.0) as source:
    #                 receive_files(arguments, source)
    #         except serial.SerialException as e:
    #             print(f'Connection failure on {arguments.serial_port.name}: {e}', file=sys.stderr)
    #             exit(1)
    # else:
    #     if arguments.serial_port is None:
    #         send_files(arguments, None)
    #     elif arguments.serial_port.name.lower() == 'clipboard':
    #         with io.BytesIO() as buffer:
    #             send_files(arguments, buffer)
    #     else:
    #         try:
    #             with serial.Serial(port=arguments.serial_port.name,
    #                                baudrate=arguments.serial_port.baud_rate,
    #                                rtscts=arguments.serial_port.flow_control_enabled,
    #                                exclusive=arguments.serial_port.exclusive_port_access_mode,
    #                                timeout=SERIAL_TIMEOUT_MS / 1000.0) as destination:
    #                 send_files(arguments, destination)
    #         except serial.SerialException as e:
    #             print(f'Connection failure on {arguments.serial_port.name}: {e}', file=sys.stderr)
    #             exit(1)


if __name__ == '__main__':
    main()
