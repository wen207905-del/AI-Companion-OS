import os

base = r'D:\AI-Companion-OS\v2\backend'
fixed = []

for root, dirs, files in os.walk(base):
    for f in files:
        if not f.endswith('.py'):
            continue
        fpath = os.path.join(root, f)

        with open(fpath, 'rb') as fh:
            raw = fh.read()

        # Strategy: double-encoded UTF-8 (UTF-8 -> Latin-1 -> UTF-8)
        # Reverse: decode as Latin-1, encode back, decode as UTF-8
        try:
            reversed_bytes = raw.decode('latin-1').encode('latin-1', errors='replace')
            text = reversed_bytes.decode('utf-8', errors='replace')
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
            if has_chinese:
                with open(fpath, 'w', encoding='utf-8') as fh:
                    fh.write(text)
                fixed.append(os.path.relpath(fpath, base) + ' [REVERSED]')
                continue
        except:
            pass

        # CP1252 variant
        try:
            reversed_bytes = raw.decode('cp1252').encode('latin-1', errors='replace')
            text = reversed_bytes.decode('utf-8', errors='replace')
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in text)
            if has_chinese:
                with open(fpath, 'w', encoding='utf-8') as fh:
                    fh.write(text)
                fixed.append(os.path.relpath(fpath, base) + ' [CP1252]')
                continue
        except:
            pass

        # UTF-8 with replace
        try:
            text = raw.decode('utf-8', errors='replace')
            text = text.replace('\u9225?', '\u2014')
            text = text.replace('\u922b?', '\u2192')
            with open(fpath, 'w', encoding='utf-8') as fh:
                fh.write(text)
            fixed.append(os.path.relpath(fpath, base) + ' [REPLACE]')
        except:
            fixed.append(os.path.relpath(fpath, base) + ' [FAILED]')

print('Fixed:')
for x in fixed:
    print(f'  {x}')
