# ATX-Convertor/antex_writer.py
"""
ANTEX file writer module for ATX-Convertor.
Exports antenna PCC data to ANTEX v1.4 format.

The writer produces files that are byte-compatible with standard ANTEX parsers
(e.g., Bernese, PCC-Explorer, igs20.atx convention).
"""

import numpy as np
from datetime import datetime


# ----------------------------
# ANTEX v1.4 Column Specifications (IGS Convention)
# ----------------------------
# Columns 1-60:  data content
# Columns 61-80: record label (right-justified)
# PCV values:    8 chars wide, right-justified, signed (+/- prefix)
# RMS values:    8 chars wide, right-justified, unsigned

SYSTEM_PREFIX_MAP = {
    'GPS': 'G', 'GLONASS': 'R', 'Galileo': 'E',
    'BDS': 'C', 'QZSS': 'J', 'SBAS': 'S', 'IRNSS': 'I'
}


def _format_pcv_value(val: float) -> str:
    """Format a single PCV value to ANTEX 8-char field (+/- prefix)."""
    if abs(val) < 0.005:
        return "   +0.00"
    sign = '+' if val >= 0 else '-'
    formatted = f"{sign}{abs(val):.2f}"
    return formatted.rjust(8)


def _format_rms_value(val: float) -> str:
    """Format a single RMS value to ANTEX 8-char field (no sign prefix)."""
    formatted = f"{abs(val):.2f}"
    return formatted.rjust(8)


def _make_label(text: str) -> str:
    """Right-pad text to fill columns 61-80 (20 chars)."""
    return text.ljust(20)


def _format_line(content: str, label: str) -> str:
    """
    Create a standard ANTEX line: content padded to 60 chars + 20-char label.
    """
    return f"{content:<60s}{label}"


# Product name as it should appear in generated text. Note the spelling: the
# folder is "ATX-Convertor", the program is "ATX-Converter".
PRODUCT_NAME = "ATX-Converter"


def _lookup_freq(freq_code, by_system):
    """Find a frequency's data in a {system: {code: value}} mapping."""
    for system in by_system:
        if freq_code in by_system[system]:
            return by_system[system][freq_code]
    return None


def _group_identical_frequencies(freq_codes, ant_pco, ant_pcv):
    """
    Group frequencies that carry exactly the same PCO and PCV.

    ANTEX 2.0 records one block per *pattern*, listing every frequency that
    shares it, e.g.

        G01   S01   E01   C01   J01                      START OF PHV

    (see antex20.pdf and the official Example.atx2). Writing one block per
    frequency instead is valid-looking but redundant, and it hides the fact
    that the calibrations are identical. The grouped form is the expected one.

    Returns a list of (codes, pco_vec, pcv_grid) in a stable order.
    """
    groups = []
    for fc in sorted(freq_codes):
        pco_vec = _lookup_freq(fc, ant_pco)
        pcv_grid = _lookup_freq(fc, ant_pcv)

        for codes, g_pco, g_pcv in groups:
            pco_same = (
                (g_pco is None and pco_vec is None) or
                (g_pco is not None and pco_vec is not None and
                 np.array_equal(g_pco, pco_vec))
            )
            pcv_same = (
                (g_pcv is None and pcv_grid is None) or
                (g_pcv is not None and pcv_grid is not None and
                 g_pcv.shape == pcv_grid.shape and np.array_equal(g_pcv, pcv_grid))
            )
            if pco_same and pcv_same:
                codes.append(fc)
                break
        else:
            groups.append(([fc], pco_vec, pcv_grid))

    return groups


def _format_phv_codes(codes) -> str:
    """Render the frequency list of a PHV record: 3 spaces + 3-char code each."""
    return "".join(f"   {c}" for c in codes)


def write_antex_v14(filepath: str, antex_data: dict,
                    comments: list = None, include_rms: bool = False,
                    antenna_comments: dict = None, antenna_meth: dict = None):
    """
    Write antenna PCC data to an ANTEX v1.4 file.

    Args:
        filepath: Output file path.
        antex_data: Parsed ANTEX data dict with keys:
            'metadata': {antenna_key: {'type', 'serial', 'dzen', 'zenith_steps'}}
            'pco': {antenna_key: {system: {freq_code: np.array([N, E, U])}}}
            'pcv': {antenna_key: {system: {freq_code: np.array(n_azi x n_zen)}}}
        comments: Header COMMENT lines from the source file, written verbatim.
        include_rms: Whether to write RMS blocks (requires 'rms' key in antex_data).
        antenna_comments: {antenna_key: [comment, ...]} - comments belonging to an
            individual antenna, written inside its block rather than in the
            header.
        antenna_meth: {antenna_key: str} - the original METH / BY / # / DATE
            content, reproduced unchanged.
    """
    lines = []
    antenna_comments = antenna_comments or {}
    antenna_meth = antenna_meth or {}

    # --- Header ---
    lines.append(_format_line("     1.4            M", "ANTEX VERSION / SYST"))
    lines.append(_format_line("A", "PCV TYPE / REFANT"))

    # Original header comments, verbatim, then exactly one note of our own.
    if comments:
        for c in comments:
            lines.append(_format_line(c[:60], "COMMENT"))
    lines.append(_format_line(
        f"Converted to ANTEX 1.4 by {PRODUCT_NAME} on "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "COMMENT"
    ))
    lines.append(_format_line("", "END OF HEADER"))

    metadata = antex_data.get('metadata', {})
    pco_data = antex_data.get('pco', {})
    pcv_data = antex_data.get('pcv', {})
    rms_data = antex_data.get('rms', {})

    for ant_key in sorted(metadata.keys()):
        meta = metadata[ant_key]
        ant_type = meta.get('type', ant_key[:20])
        ant_serial = meta.get('serial', '')
        if ant_serial.strip().upper() == 'TYPEMEAN':
            # Internal placeholder for "no serial number" — the ANTEX
            # convention for type-mean calibrations is a blank serial field.
            ant_serial = ''
        dzen = meta.get('dzen', 5.0)
        zen_steps = meta.get('zenith_steps', 19)
        zen1 = 0.0
        zen2 = (zen_steps - 1) * dzen

        # Collect all frequency codes for this antenna
        ant_pco = pco_data.get(ant_key, {})
        ant_pcv = pcv_data.get(ant_key, {})
        ant_rms = rms_data.get(ant_key, {})

        all_freq_codes = set()
        for sys_name, freqs in ant_pco.items():
            all_freq_codes.update(freqs.keys())
        for sys_name, freqs in ant_pcv.items():
            all_freq_codes.update(freqs.keys())
        num_freqs = len(all_freq_codes)

        # Determine DAZI from PCV shape
        dazi = 5.0  # default
        for sys_name, freqs in ant_pcv.items():
            for fc, pcv_grid in freqs.items():
                if pcv_grid is not None and pcv_grid.ndim == 2:
                    n_azi = pcv_grid.shape[0]
                    if n_azi > 1:
                        # n_azi rows = NOAZI + azimuth rows (0, dazi, 2*dazi, ..., 360)
                        # First row is NOAZI, remaining are 360/dazi + 1 rows
                        n_az_rows = n_azi - 1  # exclude NOAZI
                        if n_az_rows > 1:
                            dazi = 360.0 / (n_az_rows - 1)
                    break
            break

        # --- START OF ANTENNA ---
        lines.append(_format_line("", "START OF ANTENNA"))

        # TYPE / SERIAL NO (type in cols 1-20, serial in cols 21-40)
        type_field = ant_type[:20].ljust(20)
        serial_field = ant_serial[:20].ljust(20)
        lines.append(_format_line(f"{type_field}{serial_field}", "TYPE / SERIAL NO"))

        # Comments belonging to this antenna, kept with their antenna.
        for c in antenna_comments.get(ant_key, []):
            lines.append(_format_line(c[:60], "COMMENT"))

        # METH / BY / # / DATE - the original calibration method, unchanged.
        original_meth = antenna_meth.get(ant_key)
        if original_meth:
            lines.append(_format_line(original_meth[:60], "METH / BY / # / DATE"))
        else:
            lines.append(_format_line(
                f"Converted by {PRODUCT_NAME} - no METH record in the source",
                "COMMENT"
            ))
            lines.append(_format_line(
                f"{'CONVERTED':<20s}{PRODUCT_NAME:<20s}{'1':>5s}    "
                f"{datetime.now().strftime('%Y-%m-%d')}",
                "METH / BY / # / DATE"
            ))

        # DAZI
        lines.append(_format_line(f"{dazi:6.1f}", "DAZI"))

        # ZEN1 / ZEN2 / DZEN
        lines.append(_format_line(f"{zen1:6.1f}{zen2:6.1f}{dzen:6.1f}", "ZEN1 / ZEN2 / DZEN"))

        # # OF FREQUENCIES
        lines.append(_format_line(f"{num_freqs:6d}", "# OF FREQUENCIES"))

        # --- Frequency blocks ---
        sorted_freqs = sorted(all_freq_codes)

        for fc in sorted_freqs:
            # Find the system for this freq code
            sys_name = None
            pco_vec = None
            pcv_grid = None

            for sn in ant_pco:
                if fc in ant_pco[sn]:
                    sys_name = sn
                    pco_vec = ant_pco[sn][fc]
                    break
            for sn in ant_pcv:
                if fc in ant_pcv[sn]:
                    if sys_name is None:
                        sys_name = sn
                    pcv_grid = ant_pcv[sn][fc]
                    break

            if pco_vec is None and pcv_grid is None:
                continue

            # START OF FREQUENCY
            lines.append(_format_line(f"   {fc}", "START OF FREQUENCY"))

            # NORTH / EAST / UP (PCO in mm)
            if pco_vec is not None:
                lines.append(_format_line(
                    f"{pco_vec[0]:10.2f}{pco_vec[1]:10.2f}{pco_vec[2]:10.2f}",
                    "NORTH / EAST / UP"
                ))
            else:
                lines.append(_format_line(
                    f"{0.0:10.2f}{0.0:10.2f}{0.0:10.2f}",
                    "NORTH / EAST / UP"
                ))

            # PCV rows
            if pcv_grid is not None and pcv_grid.ndim == 2:
                n_azi, n_zen = pcv_grid.shape

                for row_idx in range(n_azi):
                    row = pcv_grid[row_idx, :]

                    # First row is NOAZI
                    if row_idx == 0:
                        prefix = "   NOAZI"
                    else:
                        az_val = (row_idx - 1) * dazi
                        prefix = f"{az_val:8.1f}"

                    pcv_str = prefix + ''.join(_format_pcv_value(v) for v in row)
                    lines.append(pcv_str)

            # END OF FREQUENCY
            lines.append(_format_line(f"   {fc}", "END OF FREQUENCY"))

            # RMS block (optional)
            if include_rms and ant_rms:
                rms_grid = None
                for sn in ant_rms:
                    if fc in ant_rms[sn]:
                        rms_grid = ant_rms[sn][fc]
                        break

                if rms_grid is not None and rms_grid.ndim == 2:
                    lines.append(_format_line(f"   {fc}", "START OF FREQ RMS"))
                    n_azi, n_zen = rms_grid.shape

                    for row_idx in range(n_azi):
                        row = rms_grid[row_idx, :]

                        if row_idx == 0:
                            prefix = "   NOAZI"
                        else:
                            az_val = (row_idx - 1) * dazi
                            prefix = f"{az_val:8.1f}"

                        rms_str = prefix + ''.join(_format_rms_value(v) for v in row)
                        lines.append(rms_str)

                    lines.append(_format_line(f"   {fc}", "END OF FREQ RMS"))

        # --- END OF ANTENNA ---
        lines.append(_format_line("", "END OF ANTENNA"))

    # Write to file
    with open(filepath, 'w', newline='\n') as f:
        for line in lines:
            f.write(line + '\n')

    print(f"[OK] ANTEX v1.4 written: {filepath}")
    print(f"     Antennas: {len(metadata)}")
    return filepath


def write_antex_v2(filepath: str, antex_data: dict,
                   comments: list = None,
                   antenna_comments: dict = None,
                   antenna_meth: dict = None):
    """
    Write antenna PCC data to an ANTEX v2.0 file.

    Produces files compatible with the official ANTEX 2.0 specification
    (antex20.pdf, Example.atx2).

    Args:
        filepath: Output file path.
        antex_data: Parsed ANTEX data dict (from read_antex_file or _read_antex_v2).
        comments: Header COMMENT lines from the source file, written verbatim.
        antenna_comments: {antenna_key: [comment, ...]} - comments that belong to
            an individual antenna. They are written inside that antenna's block,
            not in the header.
        antenna_meth: {antenna_key: str} - the original METH / BY / # / DATE
            content. It describes how the antenna was calibrated, so it is
            reproduced unchanged rather than overwritten.
    """
    lines = []
    antenna_comments = antenna_comments or {}
    antenna_meth = antenna_meth or {}

    # --- Header ---
    lines.append(_format_line("     2.0            M", "ANTEX VERSION / SYST"))

    # Original header comments, verbatim, then exactly one note of our own.
    if comments:
        for c in comments:
            lines.append(_format_line(c[:60], "COMMENT"))
    lines.append(_format_line(
        f"Converted to ANTEX 2.0 by {PRODUCT_NAME} on "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "COMMENT"
    ))

    # ANTENNA TYPES - detect mixed/GPS/etc
    lines.append(_format_line("MIXED", "ANTENNA TYPES"))
    lines.append(_format_line("", "REFERENCE FRAME"))
    lines.append(_format_line("", "RELEASE"))
    lines.append(_format_line("", "END OF HEADER"))

    metadata = antex_data.get('metadata', {})
    pco_data = antex_data.get('pco', {})
    pcv_data = antex_data.get('pcv', {})
    gdv_pco = antex_data.get('gdv_pco', {})
    gdv_pcv = antex_data.get('gdv_pcv', {})
    gain_data = antex_data.get('gain', {})

    for ant_key in sorted(metadata.keys()):
        meta = metadata[ant_key]
        ant_type = meta.get('type', ant_key[:30])
        is_satellite = meta.get('is_satellite', False)
        dzen = meta.get('dzen', 5.0)
        zen_steps = meta.get('zenith_steps', 19)
        zen1 = 0.0
        zen2 = (zen_steps - 1) * dzen

        # Collect all frequency codes for this antenna
        ant_pco = pco_data.get(ant_key, {})
        ant_pcv = pcv_data.get(ant_key, {})

        all_freq_codes = set()
        for sys_name, freqs in ant_pco.items():
            all_freq_codes.update(freqs.keys())
        for sys_name, freqs in ant_pcv.items():
            all_freq_codes.update(freqs.keys())

        # Determine DAZI from PCV shape
        dazi = 0.0  # 0.0 = azimuth-independent (NOAZI only)
        for sys_name, freqs in ant_pcv.items():
            for fc, pcv_grid in freqs.items():
                if pcv_grid is not None and pcv_grid.ndim == 2:
                    n_azi = pcv_grid.shape[0]
                    if n_azi > 1:
                        n_az_rows = n_azi - 1
                        if n_az_rows > 1:
                            dazi = 360.0 / (n_az_rows - 1)
                break
            break

        # --- START OF ANTENNA ---
        lines.append(_format_line("", "START OF ANTENNA"))

        # TYPE line depends on satellite vs receiver
        if is_satellite:
            svn = meta.get('svn', '')
            cospar = meta.get('cospar', '')
            # TYPE / SVN / SAT ID: type (cols 0-30), blank (30-40), SVN (40-50), COSPAR (50-60)
            type_field = ant_type[:30].ljust(30)
            svn_pad = ' ' * 10  # cols 30-40 blank
            svn_field = svn[:10].ljust(10)
            cospar_field = cospar[:10].ljust(10) if cospar else ' ' * 10
            lines.append(_format_line(
                f"{type_field}{svn_pad}{svn_field}",
                "TYPE / SVN / SAT ID"
            ))
        else:
            ant_serial = meta.get('serial', '')
            if ant_serial.strip().upper() == 'TYPEMEAN':
                # Internal placeholder for "no serial number" — the ANTEX
                # convention for type-mean calibrations is a blank serial field.
                ant_serial = ''
            type_field = ant_type[:20].ljust(20)
            serial_field = ant_serial[:20].ljust(20)
            lines.append(_format_line(
                f"{type_field}{serial_field}",
                "TYPE / SN"
            ))

        # Comments belonging to this antenna, in their proper place: after the
        # TYPE record and before METH, as in Example.atx2.
        for c in antenna_comments.get(ant_key, []):
            lines.append(_format_line(c[:60], "COMMENT"))

        # METH / BY / # / DATE - the original calibration method, reproduced
        # unchanged. Only when the source had none do we state that this file
        # was produced by conversion, and then as a COMMENT as well, so the
        # record itself never claims a calibration that did not happen.
        original_meth = antenna_meth.get(ant_key)
        if original_meth:
            lines.append(_format_line(original_meth[:60], "METH / BY / # / DATE"))
        else:
            lines.append(_format_line(
                f"Converted by {PRODUCT_NAME} - no METH record in the source",
                "COMMENT"
            ))
            lines.append(_format_line(
                f"{'CONVERTED':<20s}{PRODUCT_NAME:<20s}{'1':>5s}    "
                f"{datetime.now().strftime('%Y-%m-%d')}",
                "METH / BY / # / DATE"
            ))

        # VALID FROM / VALID UNTIL (for satellite antennas)
        if is_satellite and meta.get('valid_from'):
            vf = meta['valid_from']
            lines.append(_format_line(
                f"  {vf.year:4d}    {vf.month:02d}    {vf.day:02d}    {vf.hour:02d}    {vf.minute:02d}   {vf.second:02d}.0000000",
                "VALID FROM"
            ))
        if is_satellite and meta.get('valid_until'):
            vu = meta['valid_until']
            lines.append(_format_line(
                f"  {vu.year:4d}    {vu.month:02d}    {vu.day:02d}    {vu.hour:02d}    {vu.minute:02d}   {vu.second:02d}.9999999",
                "VALID UNTIL"
            ))

        # --- PHV blocks ---
        # One block per distinct pattern, listing every frequency that shares
        # it. "# OF PHV" therefore counts blocks, not frequencies.
        phv_groups = _group_identical_frequencies(all_freq_codes, ant_pco, ant_pcv)
        if phv_groups:
            lines.append(_format_line(f"{len(phv_groups):6d}", "# OF PHV"))
            lines.append(_format_line(f"{dazi:6.1f}", "DAZI"))
            lines.append(_format_line(f"{zen1:6.1f}{zen2:6.1f}{dzen:6.1f}", "ZEN1 / ZEN2 / DZEN"))

            for codes, pco_vec, pcv_grid in phv_groups:
                code_list = _format_phv_codes(codes)

                # START OF PHV
                lines.append(_format_line(code_list, "START OF PHV"))

                # X / Y / Z (PCO in mm)
                if pco_vec is not None:
                    lines.append(_format_line(
                        f"{pco_vec[0]:10.2f}{pco_vec[1]:10.2f}{pco_vec[2]:10.2f}",
                        "X / Y / Z"
                    ))
                else:
                    lines.append(_format_line(
                        f"{0.0:10.2f}{0.0:10.2f}{0.0:10.2f}",
                        "X / Y / Z"
                    ))

                # PCV rows
                if pcv_grid is not None and pcv_grid.ndim == 2:
                    n_azi, n_zen = pcv_grid.shape
                    for row_idx in range(n_azi):
                        row = pcv_grid[row_idx, :]
                        if row_idx == 0:
                            prefix = "   NOAZI"
                        else:
                            az_val = (row_idx - 1) * dazi
                            prefix = f"{az_val:8.1f}"
                        pcv_str = prefix + ''.join(_format_pcv_value(v) for v in row)
                        lines.append(pcv_str)

                # END OF PHV
                lines.append(_format_line(code_list, "END OF PHV"))

        # --- GDV blocks (if present) ---
        ant_gdv_pco = gdv_pco.get(ant_key, {})
        ant_gdv_pcv = gdv_pcv.get(ant_key, {})
        gdv_freq_codes = set()
        for sn, freqs in ant_gdv_pco.items():
            gdv_freq_codes.update(freqs.keys())
        for sn, freqs in ant_gdv_pcv.items():
            gdv_freq_codes.update(freqs.keys())

        if gdv_freq_codes:
            # Determine GDV zenith range from data
            gdv_zen_steps = zen_steps
            gdv_dzen = dzen
            for sn, freqs in ant_gdv_pcv.items():
                for fc, grid in freqs.items():
                    if grid is not None and grid.ndim == 2:
                        gdv_zen_steps = grid.shape[1]
                        break
                break
            gdv_zen2 = (gdv_zen_steps - 1) * gdv_dzen

            lines.append(_format_line(f"{len(gdv_freq_codes):6d}", "# OF GDV"))
            lines.append(_format_line(f"{dazi:6.1f}", "DAZI"))
            lines.append(_format_line(
                f"{zen1:6.1f}{gdv_zen2:6.1f}{gdv_dzen:6.1f}",
                "ZEN1 / ZEN2 / DZEN"
            ))

            for fc in sorted(gdv_freq_codes):
                gdv_pco_vec = None
                gdv_pcv_grid = None
                for sn in ant_gdv_pco:
                    if fc in ant_gdv_pco[sn]:
                        gdv_pco_vec = ant_gdv_pco[sn][fc]
                        break
                for sn in ant_gdv_pcv:
                    if fc in ant_gdv_pcv[sn]:
                        gdv_pcv_grid = ant_gdv_pcv[sn][fc]
                        break

                lines.append(_format_line(f"   {fc}", "START OF GDV"))
                if gdv_pco_vec is not None:
                    lines.append(_format_line(
                        f"{gdv_pco_vec[0]:10.2f}{gdv_pco_vec[1]:10.2f}{gdv_pco_vec[2]:10.2f}",
                        "X / Y / Z"
                    ))
                if gdv_pcv_grid is not None and gdv_pcv_grid.ndim == 2:
                    for row_idx in range(gdv_pcv_grid.shape[0]):
                        row = gdv_pcv_grid[row_idx, :]
                        if row_idx == 0:
                            prefix = "   NOAZI"
                        else:
                            az_val = (row_idx - 1) * dazi
                            prefix = f"{az_val:8.1f}"
                        lines.append(prefix + ''.join(_format_pcv_value(v) for v in row))
                lines.append(_format_line(f"   {fc}", "END OF GDV"))

        # --- END OF ANTENNA ---
        lines.append(_format_line("", "END OF ANTENNA"))

    # Write to file
    with open(filepath, 'w', newline='\n') as f:
        for line in lines:
            f.write(line + '\n')

    print(f"[OK] ANTEX v2.0 written: {filepath}")
    print(f"     Antennas: {len(metadata)}")
    return filepath


def convert_antex(input_path: str, output_path: str,
                  target_version: str = '2.0', comments: list = None):
    """
    Convert between ANTEX v1.4 and v2.0 formats.

    Args:
        input_path: Path to input ANTEX file (.atx or .atx2).
        output_path: Path for the output file.
        target_version: '1.4' or '2.0'.
        comments: Optional list of comment strings.

    Returns:
        Path to the written output file.
    """
    import sys, os
    # Import from PCC-Explorer's data_io for reading
    hiwi_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    explorer_dir = os.path.join(hiwi_dir, 'ImpactOfDeltaPCC')
    if explorer_dir not in sys.path:
        sys.path.insert(0, explorer_dir)

    from src.data_io import read_antex_file

    data = read_antex_file(input_path)
    src_version = data.get('antex_version', '1.4')

    if comments is None:
        comments = [f"Converted from ANTEX {src_version} to {target_version}"]

    if target_version == '2.0':
        return write_antex_v2(output_path, data, comments=comments)
    elif target_version == '1.4':
        return write_antex_v14(output_path, data, comments=comments)
    else:
        raise ValueError(f"Unsupported target version: {target_version}")
