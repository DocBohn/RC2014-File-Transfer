# RC2014-Upload

Python script to upload files to an RC2014 (or similar retrocomputers)

`upload.py` can transmit a text file as plaintext (no special encoding), or it can package a text or binary file to a
CP/M computer that has [Grant Searle's `DOWNLOAD.COM`](http://searle.x10host.com/cpm/index.html) on its A: drive.

The nominal use is with one of [Spencer Owen's RC2014 computers](https://rc2014.co.uk/) or
a [similar retrocomputer](https://smallcomputercentral.com/).

There are a handful of options;
however, a typical transmission (115.2 kilobaud, file packaged for `DOWNLOAD.COM`) can be achieved by specifying only
the port (with the `-p` option) and the file to be uploaded.

## Dependence

`upload.py` requires the `pyserial` library.

## Usage

```
python upload.py [options] source_file
```

### Options

| Argument                                       | Description                                                                                                                                                                                                                                                                                                                                                     |
|:-----------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `-h`                                           | Show the help message.                                                                                                                                                                                                                                                                                                                                          |
| `-p PORT`<br>`--port PORT`                     | The serial port used for the serial connection.<br>(See below for special cases.)                                                                                                                                                                                                                                                                               |
| `--flow-control`<br>`--no-flow-control`        | Enables/disables hardware flow control.<br>(default: enabled)                                                                                                                                                                                                                                                                                                   |
| `-b BAUDRATE`<br>`--baud BAUDRATE`             | The baud rate for the serial connection.<br>(default: 115200)                                                                                                                                                                                                                                                                                                   |
| `-d DELAY`<br>`--delay DELAY`                  | The delay (in milliseconds) between characters. This delay shouldn't be necessary if flow control is enabled.<br>(default: 0)                                                                                                                                                                                                                                   |
| `-tf FORMAT`<br>`--transmission-format FORMAT` | The transmission format.<ul><li>*package* encodes the file for `DOWNLOAD.COM`.<li>*plaintext* transmits the file without any special encoding and forces the file format to be *text*.</ul>(default: *package*)                                                                                                                                                 |
| `-ff FORMAT`<br>`--file-format FORMAT`         | The file format.<ul><li>*text* files are assumed to be human-readable files. Unix and Apple line terminators (`\n` and `\r`, respectively) will be replaced with CP/M line terminators (`\r\n`).<li>*binary* files are assumed to not be human-readable. No bytes will be added, removed, or changed.</ul>If unspecified, `upload.py` will infer the file type. |
| `-u USERNUMBER`<br>`--user USERNUMBER`         | The CP/M user number.<br>(default: 0)                                                                                                                                                                                                                                                                                                                           |

### Omitting the Serial Port

If no serial port is specified, then `upload.py` will simulate the transmission, printing only to the host computer's
console.

### Output Suitable for Copy/Paste

***TODO*** -- not yet a feature

Obviously, if you want to copy/paste *plaintext* then you can simply copy the text of the file.
On the other hand, if you want to copy/paste a *package* encoding then for now I recommend that you use
the [File Packager on the RC2014 website](https://rc2014.co.uk/filepackage/). (*n.b.*, the File Packager on the RC2014
website does not convert line terminators.)

### Inferring the File Format

- If you specify the file format using `-ff` or `--file-format` then `update.py` will use that format, unless...
- If you specify a *plaintext* transmission (using `-tf plaintext` or `--transmission-format plaintext`) then the file format will be set to *text* **even if you set the file format to *binary* using `-ff binary` or `--file-format binary`**.

If neither of those cases are at play, then `update.py` will infer the file type from the file extension if possible or from the file contents otherwise.

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

## Examples

***TODO***
