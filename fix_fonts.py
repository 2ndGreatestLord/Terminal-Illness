import re

files = ['main.py', 'ui_screens.py', 'structures.py']
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()

    if f in ['main.py', 'structures.py']:
        if 'from ui_screens import' in content and 'get_font' not in content:
            content = content.replace('from ui_screens import (', 'from ui_screens import get_font, (')
            content = content.replace('from ui_screens import ', 'from ui_screens import get_font, ')

    content = re.sub(r'pygame\.font\.SysFont\(\s*None\s*,\s*(\d+)\s*\)', r'get_font(\1)', content)
    content = re.sub(r'pygame\.font\.SysFont\(\s*None\s*,\s*(\d+)\s*,\s*bold=(\w+)\s*\)', r'get_font(\1, bold=\2)', content)
    content = re.sub(r'pygame\.font\.SysFont\(\s*[\'\"].*?[\'\"]\s*,\s*(\d+)\s*,\s*bold=(\w+)\s*\)', r'get_font(\1, bold=\2)', content)

    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
