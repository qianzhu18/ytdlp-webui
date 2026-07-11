#!/usr/bin/env node

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const args = process.argv.slice(2);
const valueAfter = (flag) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};

const domain = (valueAfter('--domain') || '').replace(/^\./, '');
const output = valueAfter('--output');
if (!domain || !output) {
  console.error('Usage: export-cdp-cookies.mjs --domain bilibili.com --output /path/to/cookies.txt');
  process.exit(2);
}

const activePortPath = path.join(
  os.homedir(),
  'Library/Application Support/Google/Chrome/DevToolsActivePort',
);

let activePort;
try {
  activePort = fs.readFileSync(activePortPath, 'utf8').trim().split(/\r?\n/);
} catch {
  console.error('Chrome remote debugging is unavailable; run the web-access dependency check first.');
  process.exit(1);
}

const [port, browserPath] = activePort;
if (!port || !browserPath) {
  console.error('Chrome DevToolsActivePort is incomplete.');
  process.exit(1);
}

const ws = new WebSocket(`ws://127.0.0.1:${port}${browserPath}`);
const timer = setTimeout(() => {
  console.error('Timed out while reading cookies from Chrome CDP.');
  ws.close();
  process.exit(1);
}, 15000);

ws.addEventListener('open', () => {
  ws.send(JSON.stringify({ id: 1, method: 'Storage.getCookies' }));
});

ws.addEventListener('message', (event) => {
  const message = JSON.parse(String(event.data));
  if (message.id !== 1) return;
  clearTimeout(timer);
  if (message.error) {
    console.error(`Chrome CDP rejected Storage.getCookies: ${message.error.message}`);
    ws.close();
    process.exit(1);
  }

  const cookies = (message.result?.cookies || []).filter((cookie) => {
    const cookieDomain = String(cookie.domain || '').replace(/^\./, '');
    return cookieDomain === domain || cookieDomain.endsWith(`.${domain}`);
  });
  const clean = (value) => String(value ?? '').replace(/[\t\r\n]/g, '');
  const lines = ['# Netscape HTTP Cookie File', '# Exported from the active Chrome session through CDP.'];
  for (const cookie of cookies) {
    const rawDomain = clean(cookie.domain);
    const includeSubdomains = rawDomain.startsWith('.') ? 'TRUE' : 'FALSE';
    const fileDomain = cookie.httpOnly ? `#HttpOnly_${rawDomain}` : rawDomain;
    lines.push([
      fileDomain,
      includeSubdomains,
      clean(cookie.path || '/'),
      cookie.secure ? 'TRUE' : 'FALSE',
      Math.max(0, Math.floor(Number(cookie.expires) || 0)),
      clean(cookie.name),
      clean(cookie.value),
    ].join('\t'));
  }

  fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true });
  fs.writeFileSync(output, `${lines.join('\n')}\n`, { mode: 0o600 });
  fs.chmodSync(output, 0o600);
  console.log(`Exported ${cookies.length} cookies for ${domain}.`);
  ws.close();
});

ws.addEventListener('error', () => {
  clearTimeout(timer);
  console.error('Unable to connect to the active Chrome CDP session.');
  process.exit(1);
});
