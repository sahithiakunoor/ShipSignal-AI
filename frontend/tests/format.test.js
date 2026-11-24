import test from 'node:test';
import assert from 'node:assert/strict';
import {count,percent,days} from '../src/format.js';
test('format calculated values without replacing missing results with zero',()=>{
 assert.equal(count(99441),'99,441');assert.equal(percent(.0812),'8.1%');assert.equal(days(12.37),'12.4 days');
 assert.equal(percent(null),'—');assert.equal(days(null),'—');assert.equal(count(null),'—');
});
