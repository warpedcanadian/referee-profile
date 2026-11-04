import assert from 'node:assert/strict';
import {seasonOf,selectGames,summarize,rankRinks,rankPartners,monthlyCounts,csv} from '../site/model.js';

const partnerA = {id: 'a', name: 'Alex A.'};
const partnerB = {id: 'b', name: 'Alex A.'};
const first = {
  date: '2027-05-31', season: '2026-27', rink: 'East Rink', level: 'Adult',
  hours: 1.25, partners: [partnerA], solo: false,
};
const second = {
  date: '2027-06-01', season: '2027-28', rink: 'East Rink', level: 'Adult',
  hours: 1.5, partners: [partnerA, partnerB, partnerA], solo: false,
};
const third = {
  date: '2027-08-03', season: '2027-28', rink: 'West Rink', level: 'Juniors',
  hours: 2, partners: [], solo: true,
};
const games = [first, second, third];

assert.deepEqual(summarize(games), {games: 3, hours: 4.75, days: 3, rinks: 2, partners: 2, solo: 1});
assert.equal(rankRinks(games)[0].games, 2);
assert.deepEqual(rankPartners(games).map(({games}) => games), [2, 1]);
assert.deepEqual(selectGames(games, {season: '2027-28', rink: 'East Rink', level: 'Adult'}), [second]);
assert.deepEqual(selectGames(games, {season: '2035-36'}), []);
assert.equal(seasonOf(first.date), '2026-27');
assert.equal(seasonOf(second.date), '2027-28');
const months = monthlyCounts(selectGames(games, {season: '2027-28'}), '2027-28', third.date);
assert.deepEqual(months.slice(0, 4).map(({value}) => value), [1, 0, 1, null]);
assert.ok(csv(games).includes('"Date","Season","Rink","Level","Hours","Partners"'));
assert.ok(csv([{...second, rink: '=1+1'}]).includes("'=1+1"));
console.log('Dashboard model checks passed.');
