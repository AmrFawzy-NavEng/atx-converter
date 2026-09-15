# ATX-Converter

Convert antenna calibrations between ANTEX v1.4 and v2.0.

> **Version 1.0, released 1 September 2026.** Download the Windows package
> from [Releases](https://github.com/J-kroeger/atx-converter/releases/latest), unzip it and start
> `ATX-Converter.exe`. No installation and no Python required. The full source code is in
> this repository.

## What it does

Converts ANTEX files between version 1.4 and version 2.0 in either direction,
and lets you keep only the antennas and signals you need on the way through.

The input format is detected automatically, and the number of antennas and
signals found is reported before anything is written, so you can see what you
are about to convert.

## Why it exists

ANTEX v2.0 carries information v1.4 cannot, and processing software has adopted
it at different speeds. A calibration you receive in one version is routinely
needed in the other. Doing that by hand on a file holding hundreds of antennas
is error-prone, and a silent mistake in a calibration file propagates into every
coordinate computed with it.

## Features

- Detects the input ANTEX version automatically
- Converts v1.4 to v2.0 and v2.0 to v1.4
- Filters by antenna, so a file of hundreds becomes a file of one
- Filters by constellation: GPS, Galileo, GLONASS, BeiDou
- Previews the output before writing it


## Running from source

The program is written in Python and was built with Python 3.12.

```
python -m pip install -r requirements.txt
python pcc_convertor.py
```

On Windows, `launch_gui.bat` does the same when no packaged executable is next to it.
The full user guide is in [`readme.txt`](readme.txt).

The `src/` folder holds the ANTEX reader shared with [PCC-Explorer](https://github.com/J-kroeger/pcc-explorer).

## Part of PCC-Suite

This program is one of seven released together as
[PCC-Suite](https://github.com/J-kroeger/pcc-suite), a collection of open-source programs for GNSS antenna
calibration values from the Institut für Erdmessung (IfE), Leibniz University
Hannover. Each is a standalone Windows executable, released and versioned
separately, so you can take only the one you need. No installation, no Python
required.

Archived releases and DOIs are gathered in the Zenodo community
[Open Source Software Packages for GNSS Data Processing](https://zenodo.org/communities/gnss-open-source-solutions).

## Licence

GNU General Public License v3.0 or later. Free to use, share and modify. See
[LICENSE](LICENSE).

## Citation

The method behind the suite and its validation against real PPP solutions are
described in:

> Kröger, J., Kersten, T. & Schön, S. (2026). PCC-Explorer: an open-source
> software tool to assess the impact of GNSS antenna phase center corrections on
> geodetic parameters. *GPS Solutions* **30**, 93. [https://doi.org/10.1007/s10291-026-02056-2](https://doi.org/10.1007/s10291-026-02056-2)

## Stay informed

Release announcements, and warnings when an external data source moves, go to
the institute software mailing list:

```
SOFTWARE-IFE@LISTSERV.UNI-HANNOVER.DE
```

The program offers to subscribe you on first start. You can decline, and you can
ask not to be reminded again.

## Contact

**Dr.-Ing. Johannes Kröger**
Institut für Erdmessung (IfE), Leibniz Universität Hannover
Schneiderberg 50, D-30167 Hannover

Email: [kroeger@ife.uni-hannover.de](mailto:kroeger@ife.uni-hannover.de)
Web: [www.ife.uni-hannover.de](https://www.ife.uni-hannover.de)
