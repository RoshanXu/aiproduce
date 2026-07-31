"""删除所有 Agent 中的降级托底代码"""
import re, os

agents_dir = "src/agents"
files = [f for f in os.listdir(agents_dir) if f.endswith('.py') and f not in ('__init__.py', 'base.py')]

for fname in files:
    path = os.path.join(agents_dir, fname)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content

    # 1. Remove "if self.prompt_template:" / else fallback pattern
    content = re.sub(
        r'(\s+)if self\.prompt_template:\s*\n\s+(\w+ = self\._llm_\w+\([^)]+\))\s*\n\s+else:\s*\n\s+\w+ = self\._(rule_based_\w+|template_generate)\([^)]+\)',
        r'\1\2',
        content
    )

    # 2. Remove try/except blocks that fall back to rule_based
    content = re.sub(
        r'(\s+)try:\s*\n\s+(response = self\.call_llm\([^)]+\))\s*\n\s+.*?\s*\n\s+except Exception as e:\s*\n\s+node_logger\.\w+\([^)]+\)\s*\n\s*\n\s+return self\._(rule_based_\w+|template_generate)\([^)]+\)',
        r'\1\2',
        content,
        flags=re.DOTALL
    )

    # 3. Delete _rule_based_* and _template_generate method blocks
    lines = content.split('\n')
    new_lines = []
    skip = False
    for line in lines:
        if re.match(r'\s+def _rule_based_\w+', line) or re.match(r'\s+def _template_generate', line):
            skip = True
            continue
        if skip:
            if (re.match(r'\s+def (?!_rule_based_|_template_generate)\w+', line)
                    or re.match(r'\s+# ───', line)):
                skip = False
                new_lines.append(line)
            continue
        new_lines.append(line)
    content = '\n'.join(new_lines)

    if content != original:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {fname}")
    else:
        print(f"OK: {fname}")

print("Done!")
