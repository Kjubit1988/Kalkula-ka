class DOMTokenList {
  constructor(element) {
    this._element = element;
  }
  _getTokens() {
    const cls = this._element.getAttribute('class') || '';
    return cls.trim().split(/\s+/).filter(Boolean);
  }
  _setTokens(tokens) {
    this._element.setAttribute('class', tokens.join(' '));
  }
  add(...tokens) {
    const current = new Set(this._getTokens());
    for (const t of tokens) {
      if (t) current.add(t);
    }
    this._setTokens(Array.from(current));
  }
  remove(...tokens) {
    const current = new Set(this._getTokens());
    for (const t of tokens) {
      current.delete(t);
    }
    this._setTokens(Array.from(current));
  }
  contains(token) {
    return this._getTokens().includes(token);
  }
  toggle(token, force) {
    const current = this.contains(token);
    const next = force !== undefined ? Boolean(force) : !current;
    if (next) {
      this.add(token);
    } else {
      this.remove(token);
    }
    return next;
  }
}

class EventTargetNode {
  constructor() {
    this._listeners = {};
  }
  addEventListener(type, listener) {
    if (!this._listeners[type]) {
      this._listeners[type] = [];
    }
    this._listeners[type].push(listener);
  }
  removeEventListener(type, listener) {
    if (!this._listeners[type]) return;
    this._listeners[type] = this._listeners[type].filter(fn => fn !== listener);
  }
  dispatchEvent(event) {
    if (!event.target) {
      event.target = this;
    }
    event.currentTarget = this;
    const listeners = (this._listeners[event.type] || []).slice();
    for (const listener of listeners) {
      if (typeof listener === 'function') {
        listener.call(this, event);
      } else if (listener && typeof listener.handleEvent === 'function') {
        listener.handleEvent(event);
      }
      if (event._stopImmediate) break;
    }
    return !event.defaultPrevented;
  }
}

class DOMElement extends EventTargetNode {
  constructor(tagName) {
    super();
    this.tagName = String(tagName).toUpperCase();
    this.attributes = {};
    this.children = [];
    this.parentNode = null;
    this._value = '';
    this._textNodeContent = '';
    this.classList = new DOMTokenList(this);
    this.dataset = new Proxy(this.attributes, {
      get: (target, prop) => {
        const attrName = 'data-' + String(prop).replace(/([A-Z])/g, '-$1').toLowerCase();
        return target[attrName];
      },
      set: (target, prop, value) => {
        const attrName = 'data-' + String(prop).replace(/([A-Z])/g, '-$1').toLowerCase();
        target[attrName] = String(value);
        return true;
      }
    });
  }

  getAttribute(name) {
    const val = this.attributes[name.toLowerCase()];
    return val !== undefined ? val : null;
  }

  setAttribute(name, value) {
    this.attributes[name.toLowerCase()] = String(value);
  }

  removeAttribute(name) {
    delete this.attributes[name.toLowerCase()];
  }

  hasAttribute(name) {
    return this.attributes[name.toLowerCase()] !== undefined;
  }

  get id() {
    return this.getAttribute('id') || '';
  }
  set id(value) {
    this.setAttribute('id', value);
  }

  get className() {
    return this.getAttribute('class') || '';
  }
  set className(value) {
    this.setAttribute('class', value);
  }

  get value() {
    return this._value !== undefined ? this._value : '';
  }
  set value(v) {
    this._value = String(v);
  }

  get textContent() {
    if (this.children.length === 0) {
      return this._textNodeContent || '';
    }
    return this.children.map(c => c.textContent).join('');
  }

  set textContent(text) {
    this.children = [];
    this._textNodeContent = String(text);
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  closest(selector) {
    let current = this;
    while (current && current instanceof DOMElement) {
      if (current._matchesSelector(selector)) {
        return current;
      }
      current = current.parentNode;
    }
    return null;
  }

  _matchesSelector(sel) {
    sel = sel.trim();
    if (sel.startsWith('#')) {
      return this.id === sel.slice(1);
    }
    if (sel.startsWith('.')) {
      return this.classList.contains(sel.slice(1));
    }
    if (sel.startsWith('[') && sel.endsWith(']')) {
      const inner = sel.slice(1, -1);
      if (inner.includes('=')) {
        const [rawName, rawVal] = inner.split('=', 2);
        const name = rawName.trim().toLowerCase();
        const expected = rawVal.trim().replace(/^['"]|['"]$/g, '');
        return this.getAttribute(name) === expected;
      }
      return this.hasAttribute(inner.trim().toLowerCase());
    }
    return this.tagName.toLowerCase() === sel.toLowerCase();
  }

  _collectDescendants(filterFn, acc = []) {
    for (const child of this.children) {
      if (filterFn(child)) {
        acc.push(child);
      }
      child._collectDescendants(filterFn, acc);
    }
    return acc;
  }

  querySelector(selector) {
    const all = this.querySelectorAll(selector);
    return all.length > 0 ? all[0] : null;
  }

  querySelectorAll(selector) {
    return this._collectDescendants(node => node._matchesSelector(selector));
  }

  click() {
    const event = {
      type: 'click',
      target: this,
      currentTarget: this,
      bubbles: true,
      defaultPrevented: false,
      _stopPropagation: false,
      _stopImmediate: false,
      stopPropagation() { this._stopPropagation = true; },
      stopImmediatePropagation() { this._stopImmediate = true; this._stopPropagation = true; },
      preventDefault() { this.defaultPrevented = true; }
    };
    let cur = this;
    while (cur) {
      cur.dispatchEvent(event);
      if (event._stopPropagation) break;
      cur = cur.parentNode;
    }
  }
}

class DOMDocument extends EventTargetNode {
  constructor() {
    super();
    this.documentElement = new DOMElement('html');
    this.body = new DOMElement('body');
    this.documentElement.appendChild(this.body);
    this.body.parentNode = this.documentElement;
    this.documentElement.parentNode = this;
  }

  getElementById(id) {
    const all = this.documentElement._collectDescendants(node => node.id === id);
    return all.length > 0 ? all[0] : null;
  }

  querySelector(selector) {
    if (this.documentElement._matchesSelector(selector)) return this.documentElement;
    return this.documentElement.querySelector(selector);
  }

  querySelectorAll(selector) {
    const res = this.documentElement.querySelectorAll(selector);
    if (this.documentElement._matchesSelector(selector)) {
      return [this.documentElement, ...res];
    }
    return res;
  }
}

const document = new DOMDocument();
const window = new EventTargetNode();
window.document = document;
global.document = document;
global.window = window;

function __buildDOM(nodeData, parentNode = null) {
  const el = new DOMElement(nodeData.tag || 'div');
  if (nodeData.attributes) {
    for (const [k, v] of Object.entries(nodeData.attributes)) {
      el.setAttribute(k, v);
    }
  }
  if (nodeData.text) {
    el.textContent = nodeData.text;
  }
  if (nodeData.children && Array.isArray(nodeData.children)) {
    for (const childData of nodeData.children) {
      const child = __buildDOM(childData, el);
      el.children.push(child);
    }
  }
  if (parentNode) {
    el.parentNode = parentNode;
  } else {
    document.body.appendChild(el);
  }
  return el;
}
global.__buildDOM = __buildDOM;

function __clickByText(text) {
  const buttons = document.querySelectorAll('button');
  for (const btn of buttons) {
    if (btn.textContent.trim() === String(text).trim()) {
      btn.click();
      return true;
    }
  }
  throw new Error('Button not found for text: ' + text);
}
global.__clickByText = __clickByText;
