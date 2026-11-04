import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from export_games import games_from_rows, export, display_name, PUBLIC_KEYS
from openpyxl.utils.datetime import CALENDAR_WINDOWS_1900

HEADERS=['PK','Game #','Month','Date','Site','Level','League','Length','Fee','Notes','Partner 1','Partner 2','Partner 3','3/4-Man','Band']
def game(date=dt.datetime(2027,6,1),p1='Alex Anders',p2=None,p3=None,hours=1):
    return [1,999,None,date,'New Rink','New Level','Private league',hours,999.99,'Private note',p1,p2,p3,None,None]

class ExportCases(unittest.TestCase):
    def test_approved_fields_and_names_only(self):
        identities={};result=games_from_rows(HEADERS,[game()],CALENDAR_WINDOWS_1900,identities)[0]
        self.assertEqual(set(result),PUBLIC_KEYS)
        self.assertEqual(result['partners'][0]['name'],'Alex A.')
        self.assertNotIn('Alex Anders',json.dumps(result))
        self.assertNotIn('Private',json.dumps(result))
        self.assertNotIn('999.99',json.dumps(result))
    def test_boundary_and_expansion(self):
        results=games_from_rows(HEADERS,[game(dt.datetime(2027,5,31)),game(dt.datetime(2027,6,1),hours=0)],CALENDAR_WINDOWS_1900,{})
        self.assertEqual([g['season'] for g in results],['2026-27','2027-28'])
        self.assertEqual(results[-1]['hours'],0)
        self.assertEqual(results[-1]['rink'],'New Rink')
    def test_label_aliases(self):
        record = game()
        record[4], record[5] = 'The Maverik Center', 'Pee Wees'
        result = games_from_rows(HEADERS, [record], CALENDAR_WINDOWS_1900, {})[0]
        self.assertEqual((result['rink'], result['level']), ('Maverik Center', 'Pee Wee'))
    def test_duplicate_partner_and_abbreviation_collision(self):
        identity={};rows=[game(p2='Alex Anders',p3='Alex Adams'),game(p1='ALEX ANDERS')]
        result=games_from_rows(HEADERS,rows,CALENDAR_WINDOWS_1900,identity)
        self.assertEqual(len(result[0]['partners']),2)
        self.assertEqual(result[0]['partners'][0]['name'],result[0]['partners'][1]['name'])
        self.assertNotEqual(result[0]['partners'][0]['id'],result[0]['partners'][1]['id'])
        self.assertEqual(result[0]['partners'][0]['id'],result[1]['partners'][0]['id'])
    def test_solo_and_numbered_entry_rows(self):
        blank=[2]+[None]*14
        result=games_from_rows(HEADERS,[blank,game(p1='Solo')],CALENDAR_WINDOWS_1900,{})
        self.assertEqual(len(result),1)
        self.assertTrue(result[0]['solo']);self.assertEqual(result[0]['partners'],[])
    def test_incomplete_record_does_not_export(self):
        with self.assertRaises(ValueError):games_from_rows(HEADERS,[game(date=None)],CALENDAR_WINDOWS_1900,{})
        with self.assertRaises(ValueError):games_from_rows(HEADERS,[game(hours=None)],CALENDAR_WINDOWS_1900,{})
    def test_nonfinite_and_formula_cache_values(self):
        with self.assertRaises(ValueError):games_from_rows(HEADERS,[game(hours=float('nan'))],CALENDAR_WINDOWS_1900,{})
        with self.assertRaises(ValueError):games_from_rows(HEADERS,[game(p1='Unknown')],CALENDAR_WINDOWS_1900,{})
    def test_name_rules(self):
        self.assertEqual(display_name('Austin Van Amen'),'Austin A.')
        self.assertEqual(display_name('Alexander (AJ) Gilbert'),'Alexander G.')

if __name__=='__main__':unittest.main()

