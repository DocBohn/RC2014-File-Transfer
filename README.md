# RC2014-Upload

Python script to upload files to an RC2014 (or similar retrocomputers)

`upload.py` can transmit a text file as plaintext (no special encoding), or it can package a text or binary file to a
CP/M computer that has [Grant Searle's `DOWNLOAD.COM`](http://searle.x10host.com/cpm/index.html) on its `A:` drive.

The nominal use is with one of [Spencer Owen's RC2014 computers](https://rc2014.co.uk/) or
a [similar retrocomputer](https://smallcomputercentral.com/).

There are a handful of options;
however, a typical transmission (115.2 kilobaud, file packaged for `DOWNLOAD.COM`) can be achieved by specifying only
the port (with the `-p` option) and the file to be uploaded.

## Dependence

`upload.py` requires the `pyserial` library and the `pyperclip` library.

## Usage

```
python upload.py [options] source_file [source_file ...]
```

### Options

| Argument                                       | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|:-----------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-h`                                           | Show the help message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `-p PORT`<br>`--port PORT`                     | The serial port used for the serial connection.<br>(See below for special cases.)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `--flow-control`<br>`--no-flow-control`        | Enables/disables hardware flow control.<br>(default: enabled)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `--exclusive-port`<br>`--no-exclusive-port`    | Enables/disables exclusive port access. (Neither shared nor exclusive access are guaranteed.)<br>(default: enabled)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `-b BAUDRATE`<br>`--baud BAUDRATE`             | The baud rate for the serial connection.<br>(default: 115200)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `-d DELAY`<br>`--delay DELAY`                  | The delay (in milliseconds) between characters. This delay shouldn't be necessary if flow control is enabled.<br>(default: 0)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `-tf FORMAT`<br>`--transmission-format FORMAT` | The transmission format.<ul><li>*package* encodes the file for `DOWNLOAD.COM`.<li>*plaintext* transmits the file without any special encoding and forces the file format to be *text*.</ul>(default: *package*)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| `-ff FORMAT`<br>`--file-format FORMAT`         | The file format.<ul><li>*text* files are assumed to be human-readable files; newlines will be converted from the transmitting computer's newline to the receiving computer's newline (unless specified otherwise).<li>*binary* files are assumed to not be human-readable. No bytes will be added, removed, or changed.</ul>If unspecified, `upload.py` will infer the file type.                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `-u USERNUMBER`<br>`--user USERNUMBER`         | The CP/M user number.<br>(default: 0)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `-rx`<br>`--receive`                           | (placeholder, currently unused)<br>Indicates that the file transfer will be to receive a file or files from the remote computer<br>(default: the file transfer will be to send a file or files to the remote computer).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `--echo`<br>`--no-echo`                        | Cause the transmission to be echoed (or not) to the local computer's console.<br>(default: echo)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `--source-newlines` [NEWLINE ...]              | Zero or more types of newlines to be converted to the destination computer's newline<ul><li>*CR* -- `'\r'` as used by Apple (6502 and classic Mac), Commodore, TRS-80, etc<li>*CRLF* -- `'\r\n'` as used by CP/M, MS-DOS, Windows, etc<li>*LF* -- `'\n'` as used by Unix (including Linux and modern Mac)<li>*LFCR* -- `'\n\r'` as used by BBC Micro<li>*system* -- use the newline that is used by the transmitting computer<ul><li>This is the host computer's newline when sending a file<li>This is CRLF when receiving a file (under the assumption that the remote computer runs CP/M)</ul><li>An empty set of source-newlines indicates that no newline conversion should take place.</ul>(default: system)<br>`--source-newlines` is applicable only to text files and is ignored for binary files. |
| `--target-newline` NEWLINE                     | The newline that the source-newlines will be converted to; the choice of newlines is the same as for `--source-newlines`.<br>(default: system)<br>When receiving a file, *system* is the host computer's newline; when sending a file, *system* is equivalent to CRLF (under the assumption that the remote computer runs CP/M).<br>`--target-newline` is applicable only to text files and is ignored for binary files. `--target-newline` is also ignored if the source-newlines is an empty set.                                                                                                                                                                                                                                                                                                         |

### Omitting the Serial Port

If no serial port is specified, then `upload.py` will simulate the transmission, printing only to the host computer's
console.

### Copying to the Host Computer's Clipboard

If *clipboard* is specified as the "serial port" (`-p clipboard`) then the encoded file will be copied to the host computer's clipboard,
making it possible for you to paste the encoded file into another application.
*n.b.*, Only the last file to be "transmitted" to the clipboard will be present on the clipboard.

### Inferring the File Format

- If you specify the file format using `-ff` or `--file-format` then `upload.py` will use that format, unless...
- If you specify a *plaintext* transmission (using `-tf plaintext` or `--transmission-format plaintext`) then the file
  format will be set to *text* **even if you set the file format to *binary* using `-ff binary`
  or `--file-format binary`**.

If neither of those cases are at play, then `upload.py` will infer the file type from the file extension if possible or
from the file contents otherwise.

- `.BIN` and `.COM` files are assumed to be *binary*.
- Source code is assumed to be *text*.
    - Assembly (`.ASM`)
    - Ada (`.ADB`, `.ADS`)
    - BASIC (`.BAS`)
    - C (`.C`, `.H`)
    - FORTRAN (`.F`, `.F77`, `.FOR`)
    - Forth (`.F`, `.FTH`, `.FS`, `.4TH`)
    - Pascal (`.PAS`)
- `.BAK` and `.TXT` files are assumed to be *text*.
- If the file's first kilobyte can be interpreted as valid UTF-8, then the file is assumed to be *text*.
- Otherwise, the file is assumed to be *binary*.

### Renaming files

When sending a file from the host computer to the remote computer, if the file's name does not fit in CP/M's 8.3 filename format,
then `upload.py` will prompt you to provide a name for the file on the remote computer.
Simply press the RETURN key to accept the suggested name, or type your preferred file name.

## Notes with Regard to BASIC

If you load BASIC on the remote computer and then transmit a `.BAS` file as *plaintext* then the program will be entered
into BASIC just as though you were hand-typing it (though faster and without typographical errors).
That will work regardless of whether you're using ROM Microsoft BASIC, CP/M Microsoft BASIC, or CP/M BBC BASIC.

If you subsequently save the file from one of the CP/M BASICs, BASIC will save the file in a slightly-compressed
format (replacing keywords with opcodes, replacing line number digits with hexadecimal values, a few other
optimizations).
BBC BASIC and Microsoft BASIC save their files in mutually-incompatible formats.

If you leave the remote computer on a CP/M command line and then transmit a `.BAS` file as a *package*, then Microsoft
BASIC will load the file and run it (unless there's a `CLS` statement; MBASIC treats that as a syntax error, but that's
easily dealt with).
BBC BASIC, on the other hand, will *not* load the file.

## Examples

### Simulating sending a BASIC program as plaintext

```
% python upload.py -tf plaintext examples/hello.bas 
Uploading file 1/1: examples/hello.bas -> HELLO.BAS
10 print "hello";\r\n
20 print " world"\r\n
\r\n

Simulated plaintext transmission of HELLO.BAS (1/1) completed in 0.001 seconds.
	File format: text (specified as inferred)
	File size:                 37
	Transmission size:         40
	Initial CRLF newlines:      0
	Initial LFCR newlines:      0
	Initial CR   newlines:      0
	Initial LF   newlines:      3
	Final   CRLF newlines:      3
```

Here we see that `HELLO.BAS` was (simulated) transmitted without any special encoding.
The only alteration was replacing the Unix newlines with CP/M newlines, resulting in 3 more bytes being transmitted than were in the original file.
(We can also make a sanity check that the number of newlines before and after are the same.)
Because no port was specified, no actual transmission was made.

### Sending a C program to `DOWNLOAD.COM`

```
% python upload.py -p /dev/tty.usbmodem02901 examples/hello.c 
Uploading file 1/1: examples/hello.c -> HELLO.C
A:DOWNLOAD HELLO.C\r\n
U0\r\n
:23 69 6E 63 6C 75 64 65 20 3C 73 74 64 69 6F 2E 68 3E 0D 0A 
0D 0A 
69 6E 74 20 6D 61 69 6E 28 29 20 7B 0D 0A 
09 70 72 69 6E 74 66 28 22 48 65 6C 6C 6F 2C 20 77 6F 72 6C 64 5C 6E 22 29 3B 0D 0A 
09 72 65 74 75 72 6E 20 30 3B 0D 0A 
7D 0D 0A 
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 >802F

Package transmission of HELLO.C to /dev/tty.usbmodem02901 (1/1) completed in 0.079 seconds.
	File format: text (specified as inferred)
	File size:                 73
	Bytes of padding:          49
	Transmission size:        286
	Initial CRLF newlines:      0
	Initial LFCR newlines:      0
	Initial CR   newlines:      0
	Initial LF   newlines:      6
	Final   CRLF newlines:      6

```

Here we see that `HELLO.C` was transmitted as a package.
In the actual transmission, there are no newline characters between the colon and the checksum, nor are there any space characters;
however, in the console echo, there are spaces between "bytes" for readability, and a newline has been added after each `\n` "byte".

The transmission size is a bit larger than the original file, but we can see why:
- The original file was 73 bytes, 6 bytes were added (`\r` characters), and 49 bytes of padding was added to the end, totalling 128 bytes (the sum of the original file, net changes to newlines, and padding should be a multiple of 128)
- For each byte, two 1-byte characters were transmitted, bringing us to 256 bytes
- The checksum delimiter and the checksum itself are five bytes (bringing us to 261)
- "A:DOWNLOAD HELLO.C\r\nU0\r\n:" is 25 1-byte characters, and now the sum is 286

### Sending a binary file to `DOWNLOAD.COM`

```
% python upload.py -p /dev/tty.usbmodem02901 examples/HELLO.COM 
Uploading file 1/1: examples/HELLO.COM -> HELLO.COM
A:DOWNLOAD HELLO.COM\r\n
U0\r\n
:97 E2 18 01 0E 09 11 0D   01 CD 80 01 C7 7A 38 30 
20 6F 6E 6C 79 0D 0A 24   ED 7B 06 00 21 80 00 4E 
44 2C EB CD 94 04 D5 2B   2B 0C E5 C5 21 23 07 34 
34 21 FF FF 39 01 30 08   B7 ED 42 DA 55 01 01 0E 
02 ED 42 DA 55 01 01 0F   00 09 44 4D 21 30 08 CD 
            ... 110 lines elided ...
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
>801B

Package transmission of HELLO.COM to /dev/tty.usbmodem02901 (1/1) completed in 0.766 seconds.
	File format: binary (specified as inferred)
	File size:               1840
	Bytes of padding:          80
	Transmission size:       3872
```

Here we see that `HELLO.COM` was transmitted as a package.
As with `HELLO.C`, spaces and newlines have been added to the console echo for readability
(though, for a binary file, we don't assume that 0x0A is (part of) a newline, and instead simply print 16 "bytes" per line).

### Sending multiple files, renaming a file, and specifying a non-existent file

```
% python upload.py --no-echo examples/hello.c* examples/foo.bar.baz examples/HELLO.COM
hello.c.asm needs to be renamed to 8.3 format [HELLO_C.ASM]: hello.asm
foo.bar.xyzzy needs to be renamed to 8.3 format [FOO_BAR.XYZ]: 
Uploading file 1/4: examples/hello.c.asm -> HELLO.ASM

Simulated package transmission of HELLO.ASM (1/4) completed in 0.025 seconds.
	File format: text (specified as inferred)
	File size:              11499
	Bytes of padding:         102
	Transmission size:      24096
	Initial CRLF newlines:      0
	Initial LFCR newlines:      0
	Initial CR   newlines:      0
	Initial LF   newlines:    431
	Final   CRLF newlines:    431

Uploading file 2/4: examples/foo.bar.xyzzy -> FOO_BAR.XYZ
File examples/foo.bar.xyzzy not found.

Simulated package transmission of FOO_BAR.XYZ (2/4) completed in 0.0 seconds.
	File format: binary (specified as inferred)
	File size:                  0
	Bytes of padding:           0
	Transmission size:          0

Uploading file 3/4: examples/HELLO.COM -> HELLO.COM

Simulated package transmission of HELLO.COM (3/4) completed in 0.007 seconds.
	File format: binary (specified as inferred)
	File size:               1840
	Bytes of padding:          80
	Transmission size:       3872

Uploading file 4/4: examples/hello.c -> HELLO.C

Simulated package transmission of HELLO.C (4/4) completed in 0.001 seconds.
	File format: text (specified as inferred)
	File size:                 73
	Bytes of padding:          49
	Transmission size:        286
	Initial CRLF newlines:      0
	Initial LFCR newlines:      0
	Initial CR   newlines:      0
	Initial LF   newlines:      6
	Final   CRLF newlines:      6
```

Here we see that we used wildcards to specify `hello.c` and `hello.c.asm`, and we also specified `foo.bar.xyzzy` and `HELLO.COM`.
The program prompted us to rename `hello.c.asm`, suggesting `HELLO_C.ASM`; we chose a different name.
The program prompted us to rename `foo.bar.xyzzy`, suggesting `FOO_BAR.XYZ`; we accepted the suggestion.
The program then iterated over the files, transmitting each in turn -- except for the non-existent `foo.bar.xyzzy`.

### Copying to the clipboard

```
% python upload.py -p clipboard examples/hello.bas 
Uploading file 1/1: examples/hello.bas -> HELLO.BAS
A:DOWNLOAD HELLO.BAS\r\n
U0\r\n
:31 30 20 70 72 69 6E 74 20 22 68 65 6C 6C 6F 22 3B 0D 0A 
32 30 20 70 72 69 6E 74 20 22 20 77 6F 72 6C 64 22 0D 0A 
0D 0A 
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 >8001

Package transmission of HELLO.BAS to clipboard (1/1) completed in 0.002 seconds.
	File format: text (specified as inferred)
	File size:                 37
	Bytes of padding:          88
	Transmission size:        288
	Initial CRLF newlines:      0
	Initial LFCR newlines:      0
	Initial CR   newlines:      0
	Initial LF   newlines:      3
	Final   CRLF newlines:      3

% pbpaste
A:DOWNLOAD HELLO.BAS
U0
:3130207072696E74202268656C6C6F223B0D0A3230207072696E74202220776F726C64220D0A0D0A00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000>8001
% pbpaste | hexdump -C
00000000  41 3a 44 4f 57 4e 4c 4f  41 44 20 48 45 4c 4c 4f  |A:DOWNLOAD HELLO|
00000010  2e 42 41 53 0d 0a 55 30  0d 0a 3a 33 31 33 30 32  |.BAS..U0..:31302|
00000020  30 37 30 37 32 36 39 36  45 37 34 32 30 32 32 36  |07072696E7420226|
00000030  38 36 35 36 43 36 43 36  46 32 32 33 42 30 44 30  |8656C6C6F223B0D0|
00000040  41 33 32 33 30 32 30 37  30 37 32 36 39 36 45 37  |A3230207072696E7|
00000050  34 32 30 32 32 32 30 37  37 36 46 37 32 36 43 36  |4202220776F726C6|
00000060  34 32 32 30 44 30 41 30  44 30 41 30 30 30 30 30  |4220D0A0D0A00000|
00000070  30 30 30 30 30 30 30 30  30 30 30 30 30 30 30 30  |0000000000000000|
*
00000110  30 30 30 30 30 30 30 30  30 30 30 3e 38 30 30 31  |00000000000>8001|
00000120

```

Here we see that by using the argument `-p clipboard`, the package was "transmitted" to the clipboard.
We used the macOS utility `pbpaste` to place the contents of the clipboard into `stdout`, and we piped that output into `hexdump` to view the underlying bytes.
The result is exactly what we would expect it to be.
