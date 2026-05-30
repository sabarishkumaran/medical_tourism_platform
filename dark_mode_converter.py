import os
import re

directories_to_scan = [
    'templates',
    'inquiries/templates',
    'blog/templates',
    'hospitals/templates',
    'accounts/templates',
    'appointments/templates',
    'payments/templates',
    'reviews/templates',
    'treatments/templates',
]

def fix_buttons(content):
    def replacer(match):
        class_str = match.group(1)
        if 'bg-slate-900' in class_str and 'text-white' in class_str:
            if 'dark:bg-' not in class_str:
                class_str = class_str.replace('bg-slate-900', 'bg-slate-900 dark:bg-slate-700')
            if 'hover:bg-sky-600' in class_str and 'dark:hover:bg-sky-500' not in class_str:
                class_str = class_str.replace('hover:bg-sky-600', 'hover:bg-sky-600 dark:hover:bg-sky-500')
            if 'hover:bg-slate-800' in class_str and 'dark:hover:bg-slate-600' not in class_str:
                class_str = class_str.replace('hover:bg-slate-800', 'hover:bg-slate-800 dark:hover:bg-slate-600')
        return f'class="{class_str}"'
    
    return re.sub(r'class="([^"]+)"', replacer, content)

files_modified = 0

for directory in directories_to_scan:
    if not os.path.exists(directory):
        continue
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    content = fix_buttons(content)
                    
                    if content != original_content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"Updated {filepath}")
                        files_modified += 1
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

print(f"\nDone! Modified {files_modified} files.")
