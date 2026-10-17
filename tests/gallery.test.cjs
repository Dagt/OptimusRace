const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function fixture(dialogSupported = true) {
  class Element {
    constructor() { this.listeners = {}; this.dataset = {}; this.files = []; this.textContent = ''; }
    addEventListener(type, callback) { this.listeners[type] = callback; }
    removeAttribute(name) { delete this[name]; }
    focus() { this.focused = true; }
    setCustomValidity(message) { this.validationMessage = message; }
  }
  const fields = new Map();
  const get = selector => {
    if (!fields.has(selector)) fields.set(selector, new Element());
    return fields.get(selector);
  };
  const viewer = get('[data-gallery-viewer]');
  viewer.querySelector = get;
  if (dialogSupported) viewer.showModal = () => { viewer.open = true; };
  viewer.close = () => { viewer.open = false; viewer.listeners.close(); };
  const upload = get('[data-gallery-upload]');
  upload.querySelector = get;
  upload.checkValidity = () => !get('input[type=file]').validationMessage;
  const links = Array.from({length: 3}, (_, i) => {
    const link = new Element();
    link.dataset.preview = `/media/gallery/photo-${i}.jpg?signature=example`;
    link.dataset.caption = i === 1 ? '<strong>Caption</strong>' : `Photo ${i}`;
    link.querySelector = () => ({alt: `Photo ${i}`});
    return link;
  });
  vm.runInNewContext(fs.readFileSync('static/gallery.js', 'utf8'), {
    document: {querySelector: get, querySelectorAll: selector => selector === '[data-gallery-photo]' ? links : [get('[data-gallery-full]')]},
  });
  return {get, viewer, upload, links};
}

test('viewer opens full branded photo, navigates and restores focus on close', () => {
  const {get, viewer, links} = fixture();
  let prevented = false;
  links[0].listeners.click({preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  assert.equal(viewer.open, true);
  assert.equal(get('[data-gallery-full]').src, links[0].dataset.preview);
  assert.equal(get('[data-gallery-prev]').disabled, true);
  get('[data-gallery-next]').listeners.click();
  assert.equal(get('[data-gallery-full]').src, links[1].dataset.preview);
  assert.equal(get('[data-gallery-caption]').textContent, '<strong>Caption</strong>');
  viewer.listeners.keydown({key: 'ArrowRight', preventDefault() {}});
  assert.equal(get('[data-gallery-next]').disabled, true);
  assert.equal(get('[data-gallery-full]').src, links[2].dataset.preview);
  viewer.listeners.keydown({key: 'ArrowLeft', preventDefault() {}});
  assert.equal(get('[data-gallery-full]').src, links[1].dataset.preview);
  get('[data-gallery-close]').listeners.click();
  assert.equal(viewer.open, false);
  assert.equal(get('[data-gallery-full]').src, undefined);
  assert.equal(links[0].focused, true);
});

test('photos offer no direct download and ordinary save gestures are discouraged', () => {
  assert.equal(fixture(false).links[0].listeners.click, undefined);
  const {links, viewer} = fixture();
  assert.equal(links[0].href, undefined);
  const f = fixture();
  let prevented = false;
  f.get('[data-gallery-full]').listeners.contextmenu({preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
  prevented = false;
  f.get('[data-gallery-full]').listeners.dragstart({preventDefault() { prevented = true; }});
  assert.equal(prevented, true);
});

test('upload validates size and count, recovers after correction and reports processing', () => {
  const {get, upload} = fixture();
  const input = get('input[type=file]');
  input.files = Array.from({length: 21}, () => ({size: 100}));
  input.listeners.change();
  assert.match(input.validationMessage, /20 fotos/);
  input.files = [{size: 16 * 1024 * 1024}];
  input.listeners.change();
  assert.match(input.validationMessage, /15 MB/);
  input.files = Array.from({length: 8}, () => ({size: 15 * 1024 * 1024}));
  input.listeners.change();
  assert.match(input.validationMessage, /100 MB/);
  input.files = [{size: 1024 * 1024}, {size: 1024 * 1024}];
  input.listeners.change();
  assert.equal(input.validationMessage, '');
  assert.match(get('[data-gallery-upload-status]').textContent, /2 fotos seleccionadas/);
  upload.listeners.submit();
  assert.equal(get('button[type=submit]').disabled, true);
  assert.match(get('[data-gallery-upload-status]').textContent, /aplicando la marca/);
});
