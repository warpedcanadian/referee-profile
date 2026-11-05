"""Read the saved Excel file and export only the approved public fields."""
from __future__ import annotations
import argparse
import datetime as dt
import gzip
import io
import json
import math
import os
import uuid
from pathlib import Path

import openpyxl
from openpyxl.utils import range_boundaries
from openpyxl.utils.datetime import from_excel

ROOT = Path(__file__).resolve().parents[1]
PARTNER_MAP = ROOT / '.local' / 'partner-map.json'
PUBLIC_KEYS = {'date', 'season', 'rink', 'level', 'hours', 'partners', 'solo'}
RINK_ALIASES = {'The Maverik Center': 'Maverik Center'}
LEVEL_ALIASES = {'PeeWee': 'Pee Wee', 'Pee Wees': 'Pee Wee', 'Squirts': 'Squirt'}
LOCATION_ALIASES = {
    'acord ice center': 'acord ice arena',
    "children's health starcenter - farmer branch": "children's health starcenter - farmers branch",
    'marathon park ice arena': 'marathon park ice rink',
    'the maverik center': 'maverik center',
}

def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)

def display_name(name: str) -> str:
    words = name.split()
    if len(words) < 2:
        raise ValueError('A partner name needs a first and last name before it can be abbreviated.')
    return f'{words[0]} {words[-1][0].upper()}.'

def date_value(value, epoch):
    if isinstance(value, dt.datetime): return value.date()
    if isinstance(value, dt.date): return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        result = from_excel(value, epoch)
        if isinstance(result, dt.datetime): return result.date()
    if isinstance(value, str):
        try: return dt.date.fromisoformat(value.strip()[:10])
        except ValueError: pass
    raise ValueError('Date must be an Excel date or YYYY-MM-DD.')

def games_from_rows(headers, rows, epoch, identity_map):
    positions = {str(v).strip(): i for i, v in enumerate(headers) if v is not None}
    required = ['Date', 'Site', 'Level', 'Length', 'Partner 1', 'Partner 2', 'Partner 3']
    if any(k not in positions for k in required):
        raise ValueError('The game source is missing one or more required columns.')
    records = []
    for number, values in enumerate(rows, 2):
        def get(key): return values[positions[key]] if positions[key] < len(values) else None
        if get('Date') in (None, ''):
            # The original tracker contains four future PK-only entry rows.
            if any(get(k) not in (None, '') for k in required if k != 'Date'):
                raise ValueError(f'Game row {number} has game details but no date. Add a date before publishing.')
            continue
        try:
            date = date_value(get('Date'), epoch)
            length = get('Length')
            if isinstance(length, bool) or not isinstance(length, (int, float)) or not math.isfinite(length) or length < 0:
                raise ValueError('Length must be a nonnegative number of hours.')
            rink, level = str(get('Site') or '').strip(), str(get('Level') or '').strip()
            if not rink or not level: raise ValueError('Site and Level must be filled in.')
            rink = RINK_ALIASES.get(rink, rink)
            level = LEVEL_ALIASES.get(level, level)
            partners, seen, solo = [], set(), False
            for key in ['Partner 1', 'Partner 2', 'Partner 3']:
                full_name = ' '.join(str(get(key) or '').split())
                if not full_name: continue
                if full_name.casefold() == 'solo': solo = True; continue
                normalized = full_name.casefold()
                if normalized in seen: continue
                seen.add(normalized)
                if normalized not in identity_map:
                    identity_map[normalized] = uuid.uuid4().hex
                partners.append({'id': identity_map[normalized], 'name': display_name(full_name)})
            start = date.year - (date.month < 6)
            record = {'date': date.isoformat(), 'season': f'{start}-{str(start+1)[-2:]}',
                'rink': rink, 'level': level, 'hours': float(length), 'partners': partners, 'solo': solo}
            assert set(record) == PUBLIC_KEYS
            records.append(record)
        except ValueError as e:
            raise ValueError(f'Game row {number}: {e}') from e
    if not records: raise ValueError('No dated games were found. The previous published data is retained.')
    return sorted(records, key=lambda r: r['date'])

def location_key(value):
    key = ' '.join(str(value).split()).casefold()
    return LOCATION_ALIASES.get(key, key)


def read_locations(sheet):
    rows = sheet.values
    headers = next(rows, ())
    columns = {str(label).strip().casefold(): index for index, label in enumerate(headers)}
    name_column = columns.get('rink', columns.get('site'))
    if name_column is None or 'city' not in columns or 'state' not in columns:
        raise ValueError('The Rinks tab needs Rink (or Site), City, and State column headers.')

    with gzip.open(ROOT / 'scripts/us-places.json.gz', 'rt', encoding='utf-8') as source:
        gazetteer = json.load(source)
    locations = {}
    for number, row in enumerate(rows, 2):
        name, city, state = (str(row[index] or '').strip() for index in (name_column, columns['city'], columns['state']))
        if not name or not city or not state:
            continue
        state = gazetteer['states'].get(state.casefold(), state.upper() if len(state) == 2 else state)
        city_key = ' '.join(city.split()).casefold()
        point = gazetteer['places'].get(state, {}).get(city_key)
        location = {'city': city, 'state': state}
        if point:
            location['latitude'], location['longitude'] = point
        key = location_key(name)
        if key in locations and locations[key] != location:
            raise ValueError(f'Rinks row {number} lists a conflicting location for {name}.')
        locations[key] = location
    return locations


def export(workbook_path: Path, output_path: Path = ROOT / 'site/data/games.json', map_path: Path = PARTNER_MAP):
    # Read a stable snapshot without saving or recalculating the user's workbook.
    before = workbook_path.stat()
    snapshot = workbook_path.read_bytes()
    after = workbook_path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Excel is still saving. The next sync will try again.')
    identities = json.loads(map_path.read_text(encoding='utf-8')) if map_path.exists() else {}
    wb = openpyxl.load_workbook(io.BytesIO(snapshot), data_only=True, read_only=False)
    try:
        if 'RawData' not in wb.sheetnames: raise ValueError('The workbook needs a RawData tab.')
        sheet = wb['RawData']
        if 'Games' in sheet.tables:
            c1, r1, c2, r2 = range_boundaries(sheet.tables['Games'].ref)
        else:
            # Supports the original tracker as well as the rebuilt native table.
            c1, r1, c2, r2 = 1, 1, 15, sheet.max_row
        iterator = sheet.iter_rows(min_row=r1, max_row=r2, min_col=c1, max_col=c2, values_only=True)
        headers = next(iterator)
        records = games_from_rows(headers, iterator, wb.epoch, identities)
        locations = read_locations(wb['Rinks']) if 'Rinks' in wb.sheetnames else None
    finally: wb.close()
    old = json.loads(output_path.read_text(encoding='utf-8')) if output_path.exists() else {}
    payload = {'schemaVersion': 1, 'dataThrough': records[-1]['date'], 'seasonStartMonth': 6,
        'privacy': {'fees': False, 'partnerNames': 'first-name-last-initial', 'equipment': False, 'notes': False},
        'games': records}
    if locations is None:
        locations = {location_key(name): entry for name, entry in old.get('rinks', {}).items()}
    rinks = {}
    for name in sorted({record['rink'] for record in records}):
        location = locations.get(location_key(name))
        if location:
            rinks[name] = location
    if rinks:
        payload['rinks'] = rinks
    if {key: value for key, value in old.items() if key != 'updatedAt'} == payload:
        return False, len(records)
    payload['updatedAt'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    # Stable random public identities keep two "Alex A." partners distinct.
    # This map contains the original names and is ignored by Git.
    atomic_json(map_path, identities)
    atomic_json(output_path, payload)
    return True, len(records)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT/'site/data/games.json')
    args = parser.parse_args()
    try:
        changed, count = export(args.workbook, args.output)
        data = json.loads(args.output.read_text(encoding='utf-8'))
        print(f'{"Exported" if changed else "Checked"} {count:,} games through {data["dataThrough"]}.')
    except (OSError, ValueError, KeyError, json.JSONDecodeError, openpyxl.utils.exceptions.InvalidFileException) as e:
        parser.exit(1, f'Export failed: {e}\n')

if __name__ == '__main__': main()

