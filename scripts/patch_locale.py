#!/usr/bin/env python3
"""Post-process marimo's exported index.html to fix the POSIX locale crash.

Some Linux environments cause Chromium to report navigator.language as
'en-US@posix', which is not a valid BCP 47 tag. marimo's react-aria
I18nProvider calls `new Intl.Locale(navigator.language)` without a
try/catch, crashing the entire app before it renders.

This script injects a small sanitization snippet before marimo's module
script that strips the POSIX @-extension from navigator.language.
"""
import sys

INJECT = """<script>
  (function () {
    var lang = navigator.language || '';
    if (lang.indexOf('@') !== -1) {
      var sanitized = lang.split('@')[0];
      try { new Intl.Locale(sanitized); } catch (e) { sanitized = 'en-US'; }
      Object.defineProperty(navigator, 'language', {
        get: function () { return sanitized; }
      });
    }
  })();
</script>
    """

MARKER = '<script type="module" crossorigin src='


def patch(path):
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()

    if MARKER not in html:
        print(f'ERROR: injection marker not found in {path}', file=sys.stderr)
        sys.exit(1)

    patched = html.replace(MARKER, INJECT + MARKER, 1)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(patched)

    print(f'Locale patch injected into {path}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: patch_locale.py <path/to/index.html>', file=sys.stderr)
        sys.exit(1)
    patch(sys.argv[1])
