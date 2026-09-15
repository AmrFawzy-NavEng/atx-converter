================================================================================
                              ATX-Converter
================================================================================

Version: 1.0
Release date: 2026-09-01

An open-source tool for converting GNSS antenna calibration files between
ANTEX v1.4 and ANTEX v2.0 formats, with antenna and signal filtering.

Part of the PCC software suite developed at the Institut für Erdmessung (IfE),
Leibniz Universität Hannover.

================================================================================
  CITATION
================================================================================

If you use this software, please cite:

  Kröger, J., Kersten, T. & Schön, S. PCC-Explorer: An open-source software
  tool to assess the impact of GNSS antenna phase center corrections on
  geodetic parameters. GPS Solut 30, 93 (2026).
  https://doi.org/10.1007/s10291-026-02056-2

A DOI for this program itself is planned with the v2.0 release of the suite;
until then please cite the paper above.

================================================================================
  QUICK START
================================================================================

  pip install -r requirements.txt
  python pcc_convertor.py

Or use the provided launcher scripts:
  - Windows:     launch_gui.bat
  - Linux/macOS: launch_gui.sh

================================================================================
  FEATURES
================================================================================

Input
-----
  * Load any ANTEX v1.4 (.atx) file
  * Auto-detect format version
  * Display antenna count, signal inventory

Antenna & Signal Filtering
--------------------------
  * Select specific antenna or export all
  * Filter by individual signals (G01, E01, R01, etc.)
  * Quick-select buttons: GPS Only, Galileo Only, Select All, Select None

Output
------
  * Export to ANTEX v1.4 format
  * Export to ANTEX v2.0 format, writing signals that share identical PCC
    values once on a common START OF PHV record (e.g. "E01 G01" with
    "# OF PHV = 2"), as the format description requires
  * Preview the output before exporting: the head of the header, the
    ATX-Converter note and the first antenna in full
  * Round-trip fidelity: read -> write -> read produces identical data

Header handling
---------------
  * Original comments are preserved
  * One comment is added stating the file was created by ATX-Converter
  * The METH / BY / # / DATE record of the source file is not modified

================================================================================
  DEPENDENCIES
================================================================================

  * Python 3.8+
  * numpy
  * ttkbootstrap (optional, for themed GUI)
  * PCC-Explorer's data_io module (for ANTEX parsing)

Note: ATX-Converter expects the ImpactOfDeltaPCC/ folder to be a sibling
directory for importing the ANTEX parser.

================================================================================
  FILE STRUCTURE
================================================================================

  ATX-Converter/
  +-- pcc_convertor.py          Main GUI application
  +-- antex_writer.py           ANTEX writer (v1.4 and v2.0)
  +-- test_roundtrip.py         Round-trip verification test
  +-- requirements.txt          Python dependencies
  +-- launch_gui.bat            Windows launcher
  +-- launch_gui.sh             Linux/macOS launcher
  +-- readme.txt                This file
  +-- LICENSE.txt               Short copyright notice

================================================================================
  CONTACT
================================================================================

  Dr.-Ing. Johannes Kröger -- kroeger@ife.uni-hannover.de

================================================================================
  LICENSE
================================================================================

This project is licensed under the GNU General Public License v3.0 or later.
See LICENSE.txt

================================================================================
  STAY INFORMED
================================================================================

  The Institut für Erdmessung runs a moderated mailing list for its GNSS
  software. It announces new releases and warns you about changes that can
  break your work, for example when a server for satellite orbit products
  moves to a new address. Every program in the suite offers this once when it
  first starts, and the Contact dialog can open it again at any time.

  Subscribe (web form):
    https://listserv.uni-hannover.de/cgi-bin/wa?SUBED1=SOFTWARE-IFE&A=1

  Subscribe by e-mail:
    send the single line   subscribe software-ife
    to                     listserv@listserv.uni-hannover.de

  Send that command line on its own. LISTSERV reads the message body line by
  line, so a signature added by your mail program can stop it.

  List address: SOFTWARE-IFE@LISTSERV.UNI-HANNOVER.DE

  LISTSERV answers with a confirmation mail. The subscription becomes active
  only after you reply to it and a moderator approves the request. Subscribing
  is voluntary and you can leave the list at any time.
