# RC2014 File Transfer

Python program to upload files to, and download files from, an RC2014 (or similar retrocomputers).

`transfer.py` can transmit text files as plaintext (no special encoding), or it can package text or binary files to a
CP/M computer that has [Grant Searle's `DOWNLOAD.COM`](http://searle.x10host.com/cpm/index.html) on its A: drive.

`transfer.py` can receive a text file as plaintext (no special encoding), or it can receive packaged text or binary
files from a CP/M computer that has
[Shirley](https://blog.peacockmedia.software/2022/01/uploadcom-for-z80-cpm-writing-utility.html) 
[Knott's](https://blog.peacockmedia.software/2022/01/uploadcom-for-z80-cpm-usage.html) 
[`UPLOAD.COM`](https://github.com/RC2014Z80/RC2014/blob/master/CPM/UPLOAD.COM/README.md) on its A: drive.

The nominal use is with one of [Spencer Owen's RC2014 computers](https://rc2014.co.uk/) or
a [similar retrocomputer](https://smallcomputercentral.com/).

There are a handful of options;
however, a typical transmission (115.2 kilobaud, file packaged for `DOWNLOAD.COM`) can be achieved by specifying only
the port (with the `-p` option) and the file to be uploaded.

## Dependence

`transfer.py` requires the `pyserial` library and the `pyperclip` library.

## Usage

```
python transfer.py [options] source_file [source_file ...]
```

### Options

| Argument                                       | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
|:-----------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-h`                                           | Show the help message.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `-p PORT`<br>`--port PORT`                     | The serial port used for the serial connection.<br>(See below for special cases.)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `--flow-control`<br>`--no-flow-control`        | Enables/disables hardware flow control.<br>(default: enabled)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `--exclusive-port`<br>`--no-exclusive-port`    | Enables/disables exclusive port access. (Neither shared nor exclusive access are guaranteed.)<br>(default: enabled)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `-b BAUDRATE`<br>`--baud BAUDRATE`             | The baud rate for the serial connection.<br>(default: 115200)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `-d DELAY`<br>`--delay DELAY`                  | The delay (in milliseconds) between characters. This delay shouldn't be necessary if flow control is enabled.<br>(default: 0)<br>Applies only when sending characters to the remote computer.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `-tf FORMAT`<br>`--transmission-format FORMAT` | The transmission format.<ul><li>*package* encodes the file for `DOWNLOAD.COM` / decodes the file from `UPLOAD.COM`.<li>*cpm-plaintext* uses CP/M commands to send/receive the file without any special encoding, and forces the file format to be *text*.<li>*basic-plaintext* assumes a BASIC editor/interpreter is open, sending/receiving the file accordingly, and forces the file format to be *text*.</ul>(default: *package*)                                                                                                                                                                                                                                                                                                                                                                        |
| `-ff FORMAT`<br>`--file-format FORMAT`         | The file format.<ul><li>*text* files are assumed to be human-readable files; newlines will be converted from the transmitting computer's newline to the receiving computer's newline (unless specified otherwise).<li>*binary* files are assumed to not be human-readable. No bytes will be added, removed, or changed.</ul>If unspecified, `transfer.py` will infer the file type.                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `-u USERNUMBER`<br>`--user USERNUMBER`         | The CP/M user number.<br>(default: 0)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `-rx`<br>`--receive`                           | Indicates that the file transfer will be to receive a file or files from the remote computer<br>(default: the file transfer will be to send a file or files to the remote computer).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `--echo`<br>`--no-echo`                        | Cause the transmission to be echoed (or not) to the local computer's console.<br>(default: echo)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `--source-newlines` [NEWLINE ...]              | Zero or more types of newlines to be converted to the destination computer's newline<ul><li>*CR* -- `'\r'` as used by Apple (6502 and classic Mac), Commodore, TRS-80, etc<li>*CRLF* -- `'\r\n'` as used by CP/M, MS-DOS, Windows, etc<li>*LF* -- `'\n'` as used by Unix (including Linux and modern Mac)<li>*LFCR* -- `'\n\r'` as used by BBC Micro<li>*system* -- use the newline that is used by the transmitting computer<ul><li>This is the host computer's newline when sending a file<li>This is CRLF when receiving a file (under the assumption that the remote computer runs CP/M)</ul><li>An empty set of source-newlines indicates that no newline conversion should take place.</ul>(default: system)<br>`--source-newlines` is applicable only to text files and is ignored for binary files. |
| `--target-newline` NEWLINE                     | The newline that the source-newlines will be converted to; the choice of newlines is the same as for `--source-newlines`.<br>(default: system)<br>When receiving a file, *system* is the host computer's newline; when sending a file, *system* is equivalent to CRLF (under the assumption that the remote computer runs CP/M).<br>`--target-newline` is applicable only to text files and is ignored for binary files. `--target-newline` is also ignored if the source-newlines is an empty set.                                                                                                                                                                                                                                                                                                         |

### Omitting the Serial Port

If no serial port is specified, then `transfer.py` will simulate the transmission, printing only to the host computer's
console.

### Copying to/from the Host Computer's Clipboard

If *clipboard* is specified as the "serial port" (`-p clipboard`) then the encoded file will be copied to/from the host
computer's clipboard, making it possible for you to paste the encoded file into, or copy the encoded file from, another
application.
*n.b.*, When sending, only the last file to be "transmitted" to the clipboard will be present on the clipboard.
When receiving, the same clipboard contents will be "received" and saved to each file.

### Notes with Regard to BASIC

#### Sending BASIC Files to a BASIC Editor/Interpreter

If you load BASIC on the remote computer and then send a file as *basic-plaintext*, then the program will be
entered into BASIC just as though you were hand-typing it (though faster and without typographical errors).
That will work regardless of whether you're using ROM Microsoft BASIC, CP/M Microsoft BASIC, or CP/M BBC BASIC.

If you subsequently save the file from one of the CP/M BASICs, BASIC will save the file in a slightly-compressed
format (replacing keywords with opcodes, replacing line number digits with hexadecimal values, a few other
optimizations).
BBC BASIC and Microsoft BASIC save their files in mutually-incompatible formats.

If you leave the remote computer on a CP/M command line and then send a `.BAS` file as a *package*, then Microsoft
BASIC will load the file and run it.[^1]<sup>,</sup>[^2]
BBC BASIC, on the other hand, will *not* load the file.

[^1]: Unless there's a `CLS` statement; CP/M MS BASIC treats that as a syntax error, but that's easily dealt with.
[^2]: Unless there's a `FOR`/`NEXT` loop; ROM MS BASIC treats that as a syntax error.

[//]: # (TODO: does ROM MBASIC also treat `CLS` as a syntax error?)

*n.b.*, If you send multiple files to a BASIC Editor/Interpreter, the effect will be as though you had typed each file's
contents in the order they were sent (which may or may not be the order in which you listed them on the command line).

#### Receiving BASIC Files

If you have a program loaded in a BASIC Editor/Interpreter, then `transfer.py` obtains its contents by using the BASIC
`LIST` command. *n.b.*, If you list multiple files, then each will have an identical copy of the source code listing.

### Notes with Regard to CP/M

#### Sending/Receiving *cpm-plaintext* Files

When sending a plaintext file to CP/M, the `C:ED.COM` editor is invoked. (***TODO***: what if the file already exists?)
When receiving a plaintext file from CP/M, the `TYPE` command is invoked.

#### Sending/Receiving *package* Files

When sending a package to CP/M, the `A:DOWNLOAD.COM` utility is invoked.
If the file being packaged is a *text* file, then `transfer.py` will convert the newlines accordingly.
Regardless of the file format, the file will be padded until its length is a multiple of 128.

When receiving a file from CP/M, the `A:UPLOAD.COM` utility is invoked.
If the file being packaged is a *text* file, then `transfer.py` will convert the newlines accordingly and remove the padding at the end of the file.

### Inferring the File Format

- If you specify the file format using `-ff` or `--file-format` then `transfer.py` will use that format, unless...
- If you specify a *plaintext* transmission (using `-tf plaintext` or `--transmission-format plaintext`) then the file
  format will be set to *text* **even if you set the file format to *binary* using `-ff binary`
  or `--file-format binary`**.

If neither of those cases are at play, then `transfer.py` will infer the file type from the file extension if possible
or
from the file contents otherwise.

- `.BIN`, `.COM`, and `.O` files are assumed to be *binary*.
- Source code is assumed to be *text*.
  - Assembly (`.ASM`, `.Z80`)
  - Ada (`.ADB`, `.ADS`)
  - BASIC (`.BAS`)
  - C (`.C`, `.H`)
  - FORTRAN (`.F`, `.F77`, `.FOR`)
  - Forth (`.F`, `.FTH`, `.FS`, `.4TH`)
  - Pascal (`.PAS`)
- Some compilation products are assumed to be *text*
  - Intel Hex (`.HEX`, `.IHX`)
  - Linker & debugger files (`.LIS`, `.LST`, `.MAP`, `.SYM`)
- Text files are assumed to be *text*
  - Text (`.TXT`)
  - Readme (`.ME`)
  - Text-based data (`.CSV`, `.JSON`, `.XML`)
  - Marked-up text files (`.MD`, `.TEX`)
- Text editor backup files (`.BAK`) are assumed to be text
- Package (`.PKG`) files are assumed to be text
  - If you have the remote computer ready at the CP/M command line, you can send a package file as *basic-plaintext*
- If the file is being *sent* to the remote computer, and its first kilobyte can be interpreted as valid ASCII, then the
  file is assumed to be *text*.
    - If the file is being *received* from the remote computer, then no such assumption is made. If a text file being
      received doesn't have an "assumed text" file extension, then consider specifying `-ff text`.
    - If a text file uses "extended ASCII" (such as 'Latin-1' or pseudographical characters) and doesn't have an 
      "assumed text" file extension, then be sure to specify `-ff text`.
- Otherwise, the file is assumed to be *binary*.

### Renaming Files

When determining the name for the new copy of a file, all path information will be stripped from original file,
leaving only the file's name.
When sending a file from the host computer to the remote computer, if the file's name does not fit in CP/M's 8.3
filename format, then `transfer.py` will prompt you to provide a name for the file on the remote computer.
Simply press the RETURN key to accept the suggested name, or type your preferred file name.

### Wildcards in File Name

You can specify multiple explicit file names when sending or receiving files.
You can also use wildcards.

When sending files, if the file name is not in quotes, then the local computer's shell will expand wildcards in the file
name, and `transfer.py` will send each file in turn.
If the file name is in quotes, then `transfer.py` will expand the wildcards and then send each file in turn.

When receiving files, you *must* enclose the file name in quotes if it includes wildcards.
If a file name with wildcards is in the list of files and is not enclosed in quotation marks, the local computer's shell
will attempt to expand the wildcards; however, it will match them based on *local* files.
If you enclose the file name in quotation marks, `transfer.py` will send the file name to the remote computer for 
wildcard expansion using the `DIR` command and parsing the output.
Since `UPLOAD.COM` can expand wildcards, this might seem to be a roundabout technique;
however, `TYPE` does not expand wildcards.
Since both `UPLOAD.COM` and `TYPE` can handle single files, it was simpler to write code that handles wildcard expansion
and then commands individual file transfers regardless of the transmission format.

## Examples

### Simulating sending a text file as BASIC plaintext

```
% python transfer.py -tf basic-plaintext examples/hello.bas

Uploading file 1/1: examples/hello.bas -> BASIC Interpreter
10 PRINT "hello";\r\n
20 PRINT " world"\r\n
\r\n

Simulated basic-plaintext transmission of HELLO.BAS (1/1) completed in 0.001 seconds. File format: text (specified as inferred)
```

Here we see that `HELLO.BAS` was (simulated) transmitted without any special encoding.
The only alteration was replacing the Unix newlines with CP/M newlines, resulting in 3 more bytes being transmitted than
were in the original file.
Because no port was specified, no actual transmission was made.

### Sending a file to the clipboard, with `--no-echo` specified

```
% python transfer.py -tf basic-plaintext -p clipboard --no-echo examples/hello.bas

Uploading file 1/1: examples/hello.bas -> BASIC Interpreter


Basic-plaintext transmission of HELLO.BAS to clipboard (1/1) completed in 0.0 seconds. File format: text (specified as inferred)
% pbpaste | cat
10 PRINT "hello";
20 PRINT " world"
```

Here we see the file being sent to the clipboard instead of to the remote computer
(`pbpaste | cat` prints the contents of the clipboard, to demonstrate that the file was copied to the clipboard).
Because `--no-echo` was specified, the transmission wasn't echoed to the console.

### Sending a text file to `ED.COM`

```
% python transfer.py -p /dev/tty.usbmodem02901 -tf cpm-plaintext examples/hello.c

Uploading file 1/1: examples/hello.c -> HELLO.C
USER 0\n
[[...........]]
ERA HELLO.C\n
[[................]]
C:ED HELLO.C\n
[[.............]]
i\n
#include <stdio.h>\r\rint main() {\r\t	printf("Hello, world\\n");\r\t	return 0;\r}\r\x1AE\n
\n
[[...........................................................................................................................................................................................]]
ERA HELLO.BAK\n
[[]]


Cpm-plaintext transmission of HELLO.C to /dev/tty.usbmodem02901 (1/1) completed in 1.337 seconds. File format: text (specified as inferred)
```

The `[[...]]` annotations are there to show bytes received back from the remote computer without cluttering the output with the actual bytes.
The astute reader will notice that the newlines were sent as `'\r'` instead of as `'\r\n'`.
That's because `ED.COM` seems to convert `'\r'` to `'\r\n'`, so `'\r\n'` becomes `'\r\n\n'`.
The important thing is that the end result is correct.
If we look at the file on the remote computer, we see that the newlines are now `'\r\n`.

```
D>TYPE HELLO.C
#include <stdio.h>

int main() {
        printf("Hello, world\n");
        return 0;
}

D>C:DUMP HELLO.C

0000 23 69 6E 63 6C 75 64 65 20 3C 73 74 64 69 6F 2E
0010 68 3E 0D 0A 0D 0A 69 6E 74 20 6D 61 69 6E 28 29
0020 20 7B 0D 0A 09 70 72 69 6E 74 66 28 22 48 65 6C
0030 6C 6F 2C 20 77 6F 72 6C 64 5C 6E 22 29 3B 0D 0A
0040 09 72 65 74 75 72 6E 20 30 3B 0D 0A 7D 0D 0A 1A
0050 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A
0060 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A
0070 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A 1A
```

### Sending a text file to `DOWNLOAD.COM`

```
% python transfer.py -p /dev/tty.usbmodem02901 examples/hello.c 

Uploading file 1/1: examples/hello.c -> HELLO.C
A:DOWNLOAD HELLO.C\n
U0\n
:23 69 6E 63 6C 75 64 65 20 3C 73 74 64 69 6F 2E 68 3E 0D 0A 
0D 0A 
69 6E 74 20 6D 61 69 6E 28 29 20 7B 0D 0A 
09 70 72 69 6E 74 66 28 22 48 65 6C 6C 6F 2C 20 77 6F 72 6C 64 5C 6E 22 29 3B 0D 0A 
09 72 65 74 75 72 6E 20 30 3B 0D 0A 
7D 0D 0A 
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 >802F
Response:  . OK


Package transmission of HELLO.C to /dev/tty.usbmodem02901 (1/1) completed in 0.309 seconds. File format: text (specified as inferred)
```

Here we see that `HELLO.C` was transmitted as a package.
In the actual transmission, there are no newline characters between the colon and the checksum, nor are there any space
characters;
however, in the console echo, there are spaces between "bytes" for readability, and a newline has been added after each
`0A` "byte".

### Sending a binary file to `DOWNLOAD.COM`

```
%% python transfer.py -p /dev/tty.usbmodem02901 examples/hello.com

Uploading file 1/1: examples/hello.com -> HELLO.COM
A:DOWNLOAD HELLO.COM\n
U0\n
:97 E2 18 01 0E 09 11 0D   01 CD 80 01 C7 7A 38 30 
20 6F 6E 6C 79 0D 0A 24   ED 7B 06 00 21 80 00 4E 
44 2C EB CD 94 04 D5 2B   2B 0C E5 C5 21 23 07 34 
34 21 FF FF 39 01 30 08   B7 ED 42 DA 55 01 01 0E 
      ... 110 lines elided for brevity ...
02 00 FE 00 00 16 08 00   00 27 08 01 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
>801B
Response:  ............... OK


Package transmission of HELLO.COM to /dev/tty.usbmodem02901 (1/1) completed in 0.998 seconds. File format: binary (specified as inferred)
```

Here we see that `HELLO.COM` was transmitted as a package.
As with `HELLO.C`, spaces and newlines have been added to the console echo for readability
(though, for a binary file, we don't assume that 0x0A is (part of) a newline, and instead simply print 16 "bytes" per
line).

### Receiving BASIC plaintext

If a BASIC editor/interpreter is loaded with a program, we can obtain that program:

```
% python transfer.py -tf basic-plaintext -p /dev/tty.usbmodem02901 -rx hello.bas

Downloading file 1/1: BASIC Interpreter -> hello.bas
LIST\r\n
LIST\r\n
10 PRINT "hello";\r\n
20 PRINT " world"\r\n
Ok\r\n



Basic-plaintext reception of hello.bas from /dev/tty.usbmodem02901 (1/1) completed in 0.22 seconds. File format: text (specified as inferred)
% cat hello.bas
10 PRINT "hello";
20 PRINT " world"
% % cat hello.bas
10 PRINT "hello";
20 PRINT " world"
% hexdump -C hello.bas 
00000000  31 30 20 50 52 49 4e 54  20 22 68 65 6c 6c 6f 22  |10 PRINT "hello"|
00000010  3b 0a 32 30 20 50 52 49  4e 54 20 22 20 77 6f 72  |;.20 PRINT " wor|
00000020  6c 64 22 0a                                       |ld".|
00000024
```

As we can see, the newlines were converted to newlines appropriate for the local system.

### Receiving a file from `TYPE`

```
% python transfer.py -tf cpm-plaintext -p /dev/tty.usbmodem02901 -rx hello.c
USER 0\n
[[...........]]
DIR HELLO.C\n
[[.................................]]

Downloading file 1/1: hello.c -> HELLO.C
TYPE hello.c\n
[[..............]]
#include <stdio.h>\r\n
\r\n
int main() {\r\n
        printf("Hello, world\\n");\r\n
        return 0;\r\n
}\r\n
\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\r\n
D>


Cpm-plaintext reception of hello.c from /dev/tty.usbmodem02901 (1/1) completed in 0.256 seconds. File format: text (specified as inferred)
% hexdump -C hello.c
00000000  23 69 6e 63 6c 75 64 65  20 3c 73 74 64 69 6f 2e  |#include <stdio.|
00000010  68 3e 0a 0a 69 6e 74 20  6d 61 69 6e 28 29 20 7b  |h>..int main() {|
00000020  0a 20 20 20 20 20 20 20  20 70 72 69 6e 74 66 28  |.        printf(|
00000030  22 48 65 6c 6c 6f 2c 20  77 6f 72 6c 64 5c 6e 22  |"Hello, world\n"|
00000040  29 3b 0a 20 20 20 20 20  20 20 20 72 65 74 75 72  |);.        retur|
00000050  6e 20 30 3b 0a 7d 0a                              |n 0;.}.|
00000057
```

You'll notice two surprising things.
The first is that `TYPE` send several ASCII `NUL` characters.
The reason for this is that the last copy of HELLO.C had been sent to the remote computer as a package, which we padded with `'\0'` characters to be consistent with the RC2014 file packager.
Had we padded the file with ASCII `SUB` characters ([as `ED.COM` did](#sending-a-text-file-to-edcom)) then `TYPE` would not have sent the `'\x1A'` characters.
However, as you can see in the hexdump, `transfer.py` stripped away the padding regardless.

The other thing you'll notice is that the original ASCII tab characters have been replaced with eight space characters.
This is the behavior of the serial connection used during these examples and is not a feature/bug of `transfer.py`.
We anticipate providing tab/spaces conversion in the future.

### Receiving a text file from `UPLOAD.COM`

```
% python transfer.py -p /dev/tty.usbmodem02901 -rx hello.c 
USER 0\n
[[...........]]
DIR HELLO.C\n
[[.................................]]

Downloading file 1/1: hello.c -> HELLO.C
A:UPLOAD hello.c\n
[[......................]]
A:DOWNLOAD HELLO.C\r\n
U0\r\n
:
23 69 6E 63 6C 75 64 65 20 3C 73 74 64 69 6F 2E 68 3E 0D 0A 
0D 0A 
69 6E 74 20 6D 61 69 6E 28 29 20 7B 0D 0A 
09 70 72 69 6E 74 66 28 22 48 65 6C 6C 6F 2C 20 77 6F 72 6C 64 5C 6E 22 29 3B 0D 0A 
09 72 65 74 75 72 6E 20 30 3B 0D 0A 
7D 0D 0A 
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 >802F
[[..........]]


Package reception of hello.c from /dev/tty.usbmodem02901 (1/1) completed in 0.319 seconds. File format: text (specified as inferred)
```

We see that the console echo as the same attempt at providing some readability as when sending a file to `DOWNLOAD.COM`.

### Receiving a binary file from `UPLOAD.COM`

```
% python transfer.py -p /dev/tty.usbmodem02901 -rx hello.com
USER 0\n
[[...........]]
DIR HELLO.COM\n
[[...................................]]

Downloading file 1/1: hello.com -> HELLO.COM
A:UPLOAD hello.com\n
[[........................]]
A:DOWNLOAD HELLO.COM\r\n
U0\r\n
:
97 E2 18 01 0E 09 11 0D   01 CD 80 01 C7 7A 38 30 
20 6F 6E 6C 79 0D 0A 24   ED 7B 06 00 21 80 00 4E 
44 2C EB CD 94 04 D5 2B   2B 0C E5 C5 21 23 07 34 
      ... 110 lines elided for brevity ...
00 FE 00 00 18 08 05 08   C3 61 07 80 00 00 00 00 
02 00 FE 00 00 16 08 00   00 27 08 01 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
>801B
[[..........]]


Package reception of hello.com from /dev/tty.usbmodem02901 (1/1) completed in 1.158 seconds. File format: binary (specified as inferred)
```

We see that the console echo as the same attempt at providing some readability as when sending a file to `DOWNLOAD.COM`.

### Sending multiple files, renaming a file, and specifying a non-existent file

```
% python transfer.py -p /dev/tty.usbmodem02901 --no-echo examples/hello.c* examples/foo.bar.baz examples/HELLO.COM
No file matching "examples/foo.bar.baz"
hello.c.asm needs to be renamed to 8.3 format [HELLO-C.ASM]: hello.asm

Uploading file 1/3: examples/HELLO.COM -> HELLO.COM

Response:  ............... OK


Package transmission of HELLO.COM to /dev/tty.usbmodem02901 (1/3) completed in 1.042 seconds. File format: binary (specified as inferred)

Uploading file 2/3: examples/hello.c -> HELLO.C

Response: D>A:DOWNLOAD HELLO.C  . OK


Package transmission of HELLO.C to /dev/tty.usbmodem02901 (2/3) completed in 0.309 seconds. File format: text (specified as inferred)

Uploading file 3/3: examples/hello.c.asm -> HELLO.ASM

Response: D>A:DOWNLOAD HELLO.ASM  ................................................................ .............................. OK


Package transmission of HELLO.ASM to /dev/tty.usbmodem02901 (3/3) completed in 4.881 seconds. File format: text (specified as inferred)
```

Here we see that we used wildcards to specify `hello.c` and `hello.c.asm`, and we also specified `foo.bar.xyzzy` and
`HELLO.COM`.
The program warns us that `foo.bar.xyzzy` doesn't exist.
The program then prompted us to rename `hello.c.asm`, suggesting `HELLO-C.ASM`; we chose a different name.
The program then iterated over the files, transmitting each in turn -- except for the non-existent `foo.bar.xyzzy`.

(We used `--no-echo` here for brevity.
Allowing the echo to show transmission progress would've made the 4.9 seconds needed to transmit `HELLO.ASM` feel shorter.)

### Receiving multiple files

```
% python transfer.py -p /dev/tty.usbmodem02901 -rx "D:HELLO.*"
USER 0\n
[[...........]]
DIR D:HELLO.*\n
[[...............................................................]]

Downloading file 1/3: D:HELLO.COM -> HELLO.COM
A:UPLOAD D:HELLO.COM\n
[[..........................]]
A:DOWNLOAD HELLO.COM\r\n
U0\r\n
:
97 E2 18 01 0E 09 11 0D   01 CD 80 01 C7 7A 38 30 
20 6F 6E 6C 79 0D 0A 24   ED 7B 06 00 21 80 00 4E 
44 2C EB CD 94 04 D5 2B   2B 0C E5 C5 21 23 07 34 
34 21 FF FF 39 01 30 08   B7 ED 42 DA 55 01 01 0E 
02 ED 42 DA 55 01 01 0F   00 09 44 4D 21 30 08 CD 
5E 01 CD 97 06 E5 E1 C7   7E 23 66 6F B4 C9 54 5D 
      ... 110 lines elided for brevity ...
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
00 00 00 00 00 00 00 00   00 00 00 00 00 00 00 00 
>801B
[[..........]]


Package reception of D:HELLO.COM from /dev/tty.usbmodem02901 (1/3) completed in 1.21 seconds. File format: binary (specified as inferred)

Downloading file 2/3: D:HELLO.ASM -> HELLO.ASM
A:UPLOAD D:HELLO.ASM\n
[[..........................]]
A:DOWNLOAD HELLO.ASM\r\n
U0\r\n
:
3B 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 0D 0A 
3B 20 46 69 6C 65 20 43 72 65 61 74 65 64 20 62 79 20 53 44 43 43 20 3A 20 66 72 65 65 20 6F 70 65 6E 20 73 6F 75 72 63 65 20 49 53 4F 20 43 20 43 6F 6D 70 69 6C 65 72 0D 0A 
3B 20 56 65 72 73 69 6F 6E 20 34 2E 34 2E 30 20 23 31 34 36 34 38 20 28 4D 61 63 20 4F 53 20 58 20 70 70 63 29 0D 0A 
3B 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 0D 0A 
3B 20 50 72 6F 63 65 73 73 65 64 20 62 79 20 5A 38 38 44 4B 0D 0A 
3B 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 2D 0D 0A 
      ... 420 lines elided for brevity ...
09 53 45 43 54 49 4F 4E 20 72 6F 64 61 74 61 5F 63 6F 6D 70 69 6C 65 72 0D 0A 
5F 5F 5F 73 74 72 5F 31 3A 0D 0A 
09 44 45 46 4D 20 22 48 65 6C 6C 6F 2C 20 77 6F 72 6C 64 22 0D 0A 
09 44 45 46 42 20 30 78 30 30 0D 0A 
09 53 45 43 54 49 4F 4E 20 49 47 4E 4F 52 45 0D 0A 
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 >00E0
[[..........]]


Package reception of D:HELLO.ASM from /dev/tty.usbmodem02901 (2/3) completed in 5.939 seconds. File format: text (specified as inferred)

Downloading file 3/3: D:HELLO.C -> HELLO.C
A:UPLOAD D:HELLO.C\n
[[........................]]
A:DOWNLOAD HELLO.C\r\n
U0\r\n
:
23 69 6E 63 6C 75 64 65 20 3C 73 74 64 69 6F 2E 68 3E 0D 0A 
0D 0A 
69 6E 74 20 6D 61 69 6E 28 29 20 7B 0D 0A 
09 70 72 69 6E 74 66 28 22 48 65 6C 6C 6F 2C 20 77 6F 72 6C 64 5C 6E 22 29 3B 0D 0A 
09 72 65 74 75 72 6E 20 30 3B 0D 0A 
7D 0D 0A 
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 >802F
[[..........]]


Package reception of D:HELLO.C from /dev/tty.usbmodem02901 (3/3) completed in 0.369 seconds. File format: text (specified as inferred)
```

Here we see that when using wildcards to identify files on the remote computer, the string needs to be enclosed in quotation marks.
