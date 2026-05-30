import os
import glob

template_dir = r"c:\Users\Sabarish Kumaran\Desktop\medical_tourism_platform\templates"
html_files = glob.glob(os.path.join(template_dir, '**', '*.html'), recursive=True)

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'inquiry.id' in content:
        new_content = content.replace('inquiry.id', 'inquiry.uuid')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {file_path}")
