import re
with open('Brain/agent_loop.py', 'r') as f:
    content = f.read()

old = '''    + "\n\nIMPORTANT: All file paths must be RELATIVE to the project root (e.g. 'file.txt', 'subdir/file.txt'). NEVER use absolute paths like C:\\ or D:\\ -- they will be rejected.'

Rules: verify file writes by reading the file back; if a command fails,'''

new = '''    + "\n\nIMPORTANT: All file paths must be RELATIVE to the project root (e.g. 'file.txt', 'subdir/file.txt'). NEVER use absolute paths like C:\\\\\\\\ or D:\\\\\\\\ -- they will be rejected.\n"
    + "Rules: verify file writes by reading the file back; if a command fails,'''

content = content.replace(old, new)

with open('Brain/agent_loop.py', 'w') as f:
    f.write(content)
print('Fixed')
