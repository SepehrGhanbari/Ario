'use strict';
// RESEARCH_ONLY v0.4. Historical verification is time-stable, nonce reuse is rejected.
// Local journal and caller-supplied key pins are NOT independent administrative custody.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const floor = require('./a15_external_floor_simulator_v0_4.js');

const MAX_BYTES = 1048576;
const MAX_EVENTS = 1000;
const STATE_FILES = new Set(['pin.json', 'minimum.jsonl']);

function fail(code) { throw Object.assign(new Error(code), {code}); }
function isRecord(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }
function canonical(value) { return JSON.stringify(value); }
function syncDirectory(dir) {
  if (process.platform === 'win32') fail('HOLD_DIRECTORY_FSYNC_UNAVAILABLE');
  let fd;
  try { fd = fs.openSync(dir, 'r'); fs.fsyncSync(fd); }
  catch { fail('HOLD_DIRECTORY_FSYNC'); }
  finally { if (fd !== undefined) fs.closeSync(fd); }
}
function uid() {
  if (typeof process.getuid !== 'function') fail('HOLD_OS_IDENTITY_UNAVAILABLE');
  return process.getuid();
}
function assertNoSymlinkComponents(target) {
  const resolved = path.resolve(target);
  const parsed = path.parse(resolved);
  let current = parsed.root;
  const segments = resolved.slice(parsed.root.length).split(path.sep).filter(Boolean);
  for (const segment of segments) {
    current = path.join(current, segment);
    let stat;
    try { stat = fs.lstatSync(current); }
    catch (error) {
      if (error.code === 'ENOENT') continue;
      fail('HOLD_PATH_INSPECTION_FAILED');
    }
    if (stat.isSymbolicLink()) fail('HOLD_STATE_SYMLINK');
  }
  return resolved;
}
function assertDirectory(dir) {
  const resolved = assertNoSymlinkComponents(dir);
  let stat;
  try { stat = fs.lstatSync(resolved); } catch { fail('HOLD_STATE_MISSING'); }
  if (!stat.isDirectory() || stat.uid !== uid() || (stat.mode & 0o077) !== 0) fail('HOLD_OPERATOR_DIRECTORY_PERMISSIONS');
  let real;
  try { real = fs.realpathSync(resolved); } catch { fail('HOLD_STATE_PATH_UNRESOLVED'); }
  if (real !== resolved) fail('HOLD_STATE_SYMLINK');
  return resolved;
}
function assertSafeParent(parent) {
  const resolved = assertNoSymlinkComponents(parent);
  let stat;
  try { stat = fs.lstatSync(resolved); } catch { fail('HOLD_STATE_PARENT_MISSING'); }
  if (!stat.isDirectory() || stat.uid !== uid() || (stat.mode & 0o022) !== 0) fail('HOLD_STATE_PARENT_UNSAFE');
}
function safeRead(dir, name, max = MAX_BYTES) {
  if (!STATE_FILES.has(name)) fail('HOLD_STATE_FILE_NAME');
  const file = path.join(dir, name);
  let before;
  try { before = fs.lstatSync(file); } catch { fail('HOLD_STATE_MISSING'); }
  if (before.isSymbolicLink() || !before.isFile() || before.uid !== uid() || (before.mode & 0o077) !== 0) fail('HOLD_STATE_FILE_PERMISSIONS');
  let fd;
  try {
    const flags = fs.constants.O_RDONLY | (fs.constants.O_NOFOLLOW || 0);
    fd = fs.openSync(file, flags);
    const after = fs.fstatSync(fd);
    if (!after.isFile() || after.dev !== before.dev || after.ino !== before.ino || after.uid !== uid() || (after.mode & 0o077) !== 0) fail('HOLD_STATE_FILE_CHANGED');
    const chunks = [];
    let size = 0;
    const buffer = Buffer.alloc(16384);
    while (true) {
      const count = fs.readSync(fd, buffer, 0, buffer.length, null);
      if (!count) break;
      size += count;
      if (size > max) fail('HOLD_STATE_BYTES');
      chunks.push(Buffer.from(buffer.subarray(0, count)));
    }
    if (!size) fail('HOLD_STATE_EMPTY');
    return Buffer.concat(chunks).toString('utf8');
  } catch (error) {
    if (error.code && error.code.startsWith('HOLD_')) throw error;
    fail('HOLD_STATE_READ');
  } finally { if (fd !== undefined) fs.closeSync(fd); }
}
function parseCanonical(raw) {
  let value;
  try { value = JSON.parse(raw); } catch { fail('HOLD_STATE_CORRUPT'); }
  if (canonical(value) !== raw) fail('HOLD_STATE_NONCANONICAL');
  return value;
}
function atomicCreate(file, text, dir) {
  let fd;
  try {
    fd = fs.openSync(file, 'wx', 0o600);
    fs.writeFileSync(fd, text, 'utf8');
    fs.fsyncSync(fd);
  } catch { fail('HOLD_STATE_CREATE'); }
  finally { if (fd !== undefined) fs.closeSync(fd); }
  syncDirectory(dir);
}
function atomicReplace(file, text, dir) {
  const tmp = path.join(dir, `.a15-v04-${process.pid}-${crypto.randomBytes(12).toString('hex')}.tmp`);
  let fd;
  try {
    fd = fs.openSync(tmp, 'wx', 0o600);
    fs.writeFileSync(fd, text, 'utf8');
    fs.fsyncSync(fd);
    fs.closeSync(fd);
    fd = undefined;
    fs.renameSync(tmp, file);
    syncDirectory(dir);
  } catch (error) {
    if (fd !== undefined) fs.closeSync(fd);
    try { fs.unlinkSync(tmp); } catch {}
    if (error.code && error.code.startsWith('HOLD_')) throw error;
    fail('HOLD_DURABLE_WRITE');
  }
}
function verifyPins(floorPublicKey, expectedFloorSha256, authorityPublicKey, expectedAuthoritySha256) {
  if (!floorPublicKey || !authorityPublicKey || !/^[0-9a-f]{64}$/.test(expectedFloorSha256 || '') ||
      !/^[0-9a-f]{64}$/.test(expectedAuthoritySha256 || '')) fail('HOLD_AUTHORITY_NOT_ESTABLISHED');
  if (floor.sha256(Buffer.from(floorPublicKey)) !== expectedFloorSha256 ||
      floor.sha256(Buffer.from(authorityPublicKey)) !== expectedAuthoritySha256) fail('HOLD_AUTHORITY_NOT_ESTABLISHED');
}
function init(dir, floorPublicKey, expectedFloorSha256, authorityPublicKey, expectedAuthoritySha256) {
  verifyPins(floorPublicKey, expectedFloorSha256, authorityPublicKey, expectedAuthoritySha256);
  const resolved = assertNoSymlinkComponents(dir);
  if (fs.existsSync(resolved)) {
    assertDirectory(resolved);
    fail('HOLD_ALREADY_INITIALIZED');
  }
  assertSafeParent(path.dirname(resolved));
  try { fs.mkdirSync(resolved, {mode: 0o700}); } catch { fail('HOLD_STATE_CREATE'); }
  assertDirectory(resolved);
  const pin = {
    v: 1,
    epoch: floor.EPOCH,
    floor_public_key: Buffer.from(floorPublicKey).toString('utf8'),
    floor_sha256: expectedFloorSha256,
    authority_public_key: Buffer.from(authorityPublicKey).toString('utf8'),
    authority_sha256: expectedAuthoritySha256,
  };
  atomicCreate(path.join(resolved, 'pin.json'), canonical(pin), resolved);
  atomicCreate(path.join(resolved, 'minimum.jsonl'), canonical({v: 1, kind: 'GENESIS', seq: 0, head: floor.ZERO}) + '\n', resolved);
  return {status: 'OPERATOR_MINIMUM_INITIALIZED_SYNTHETIC_ONLY', seq: 0, head: floor.ZERO, independent_custody: 'NOT_ESTABLISHED'};
}
function validatePin(pin) {
  if (!isRecord(pin) || Object.keys(pin).join(',') !== 'v,epoch,floor_public_key,floor_sha256,authority_public_key,authority_sha256' ||
      pin.v !== 1 || pin.epoch !== floor.EPOCH || !/^[0-9a-f]{64}$/.test(pin.floor_sha256 || '') ||
      !/^[0-9a-f]{64}$/.test(pin.authority_sha256 || '') ||
      floor.sha256(Buffer.from(pin.floor_public_key || '')) !== pin.floor_sha256 ||
      floor.sha256(Buffer.from(pin.authority_public_key || '')) !== pin.authority_sha256) fail('HOLD_PIN_CORRUPT');
  return pin;
}
function readState(dir) {
  const resolved = assertDirectory(dir);
  const entries = fs.readdirSync(resolved);
  for (const entry of entries) {
    if (!STATE_FILES.has(entry) && entry !== 'minimum.lock') fail('HOLD_RECOVERY_REQUIRED');
  }
  const pin = validatePin(parseCanonical(safeRead(resolved, 'pin.json', 16384)));
  const raw = safeRead(resolved, 'minimum.jsonl');
  if (!raw.endsWith('\n')) fail('HOLD_JOURNAL_TRUNCATED');
  const lines = raw.slice(0, -1).split('\n');
  if (!lines.length || lines.length > MAX_EVENTS + 1) fail('HOLD_JOURNAL_LIMIT');
  const genesis = parseCanonical(lines[0]);
  if (!isRecord(genesis) || Object.keys(genesis).join(',') !== 'v,kind,seq,head' ||
      genesis.v !== 1 || genesis.kind !== 'GENESIS' || genesis.seq !== 0 || genesis.head !== floor.ZERO) fail('HOLD_BAD_GENESIS');
  let seq = 0;
  let head = floor.ZERO;
  const events = [];
  const consumedNonces = new Set();
  let lastAcceptedAt = 0;
  for (const line of lines.slice(1)) {
    const item = parseCanonical(line);
    if (!isRecord(item) || Object.keys(item).join(',') !== 'v,kind,seq,head,signed' || item.v !== 1 ||
        item.kind !== 'ADVANCE' || item.seq !== seq + 1 || typeof item.head !== 'string' ||
        !floor.verifyAdvance(item.signed, pin.floor_public_key, pin.authority_public_key, pin.authority_sha256)) fail('HOLD_JOURNAL_INVALID');
    const payload = item.signed.payload;
    if (payload.seq !== item.seq || payload.prev !== head || payload.head !== item.head) fail('HOLD_JOURNAL_FORK');
    const nonceKey = floor.nonceKey(payload.authorization, pin.authority_sha256);
    if (consumedNonces.has(nonceKey)) fail('HOLD_NONCE_REUSE_HISTORICAL');
    if (payload.accepted_at < lastAcceptedAt) fail('HOLD_HISTORICAL_TIME_ORDER');
    consumedNonces.add(nonceKey);
    lastAcceptedAt = payload.accepted_at;
    seq = item.seq;
    head = item.head;
    events.push(item.signed);
  }
  return {dir: resolved, pin, seq, head, events, consumedNonces, lastAcceptedAt};
}
function evaluate(state, candidate) {
  if (!isRecord(candidate) || Object.keys(candidate).join(',') !== 'events' || !Array.isArray(candidate.events) ||
      candidate.events.length > MAX_EVENTS) fail('HOLD_CANDIDATE_INVALID');
  if (candidate.events.length === 0) return {status: 'MATCHES_RETAINED_MINIMUM_ONLY', lines: [], seq: state.seq, head: state.head};
  let seq = state.seq;
  let head = state.head;
  const lines = [];
  const consumedNonces = new Set(state.consumedNonces);
  let lastAcceptedAt = state.lastAcceptedAt;
  for (const signed of candidate.events) {
    if (!floor.verifyAdvance(signed, state.pin.floor_public_key, state.pin.authority_public_key, state.pin.authority_sha256)) fail('HOLD_EVENT_AUTHORITY_OR_SIGNATURE');
    const payload = signed.payload;
    const nonceKey = floor.nonceKey(payload.authorization, state.pin.authority_sha256);
    if (consumedNonces.has(nonceKey)) fail('HOLD_NONCE_REUSE');
    if (payload.accepted_at < lastAcceptedAt) fail('HOLD_HISTORICAL_TIME_ORDER');
    if (payload.seq !== seq + 1 || payload.prev !== head) fail(payload.seq <= seq ? 'HOLD_ROLLBACK' : 'HOLD_FORK_OR_GAP');
    consumedNonces.add(nonceKey);
    lastAcceptedAt = payload.accepted_at;
    seq = payload.seq;
    head = payload.head;
    lines.push(canonical({v: 1, kind: 'ADVANCE', seq, head, signed}) + '\n');
  }
  return {status: 'MINIMUM_ADVANCED_SYNTHETIC_ONLY', lines, seq, head};
}
function audit(dir, candidate, commit = false) {
  const state = readState(dir);
  if (!candidate || !Array.isArray(candidate.events)) fail('HOLD_CANDIDATE_INVALID');
  if (!commit) return evaluate(state, candidate);
  const lockPath = path.join(state.dir, 'minimum.lock');
  let lockFd;
  try {
    lockFd = fs.openSync(lockPath, 'wx', 0o600);
    fs.fsyncSync(lockFd);
    syncDirectory(state.dir);
  } catch { if (lockFd !== undefined) fs.closeSync(lockFd); fail('HOLD_OPERATOR_LOCKED'); }
  try {
    const fresh = readState(state.dir);
    const result = evaluate(fresh, candidate);
    if (result.lines.length) {
      const current = safeRead(fresh.dir, 'minimum.jsonl');
      atomicReplace(path.join(fresh.dir, 'minimum.jsonl'), current + result.lines.join(''), fresh.dir);
    }
    const after = readState(fresh.dir);
    return {...result, status: result.lines.length ? 'MINIMUM_ADVANCED_SYNTHETIC_ONLY' : result.status,
      committed: result.lines.length > 0, seq: after.seq, head: after.head, independent_custody: 'NOT_ESTABLISHED'};
  } finally {
    if (lockFd !== undefined) fs.closeSync(lockFd);
    try { fs.unlinkSync(lockPath); syncDirectory(state.dir); } catch { fail('HOLD_LOCK_CLEANUP'); }
  }
}
function recoveryStatus() {
  return {status: 'HOLD_EXTERNAL_CUSTODIAN_NOT_ESTABLISHED', changed: false, independent_custody: 'NOT_ESTABLISHED'};
}

module.exports = Object.freeze({init, readState, evaluate, audit, recoveryStatus, assertNoSymlinkComponents});
