#!/usr/bin/env node
// ponytail: minimal assert-based demo for model-selection heuristic; no framework.
const assert = require('assert');

function isReasoningHeavy(prompt) {
  return /reasoning|complex|heavy|improve.*model|model.*selection|discover.*model|select.*model/i.test(prompt || '');
}

assert.strictEqual(isReasoningHeavy('Improve model selection'), true, 'reasoning-heavy keyword');
assert.strictEqual(isReasoningHeavy('Push a fix'), false, 'simple prompt');
assert.strictEqual(isReasoningHeavy('Reasoning-heavy task like 35415994991'), true, 'run reference');
console.log('OK: selection heuristic passes');
