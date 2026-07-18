# -*- coding: utf-8 -*-
import re, os

with open('public/index.html', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

print("=== 菜单关键路径检测 ===")
checks = [
    ('主页 (/)', 'href=/'),
    ('关于 (/about)', '/about'),
    ('归档 (/archives)', '/archives'),
    ('搜索 (/search)', '/search'),
    ('上线通知文章', '/launch-announcement'),
    ('备案号', '津ICP备2026009218号'),
]
all_pass = True
for name, keyword in checks:
    found = keyword in content
    status = '[PASS]' if found else '[FAIL]'
    if not found:
        all_pass = False
    print(f"  {status} {name}")

print()
print("=== 页脚 beian section ===")
if 'class=beian' in content or 'class="beian"' in content:
    print("  [PASS] beian 节点存在")
else:
    print("  [FAIL] beian 节点不存在")

print()
print("总体:", "PASSED" if all_pass else "FAILED")

# 验证各页面是否生成
print()
print("=== 各页面生成验证 ===")
pages = {
    '主页': 'public/index.html',
    '关于页面': 'public/about/index.html',
    '归档页面': 'public/archives/index.html',
    '搜索页面': 'public/search/index.html',
    '上线通知': 'public/p/launch-announcement/index.html',
}
for name, path in pages.items():
    exists = os.path.exists(path)
    print(f"  {'[PASS]' if exists else '[FAIL]'} {name}: {path}")