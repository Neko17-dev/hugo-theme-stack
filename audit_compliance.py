# -*- coding: utf-8 -*-
"""
ICP 备案合规审计脚本 v1.1
审计对象: hugo-theme-stack 站点
"""
import os
import re
import json
import glob

BEIAN_ID = "津ICP备2026009218号"
BEIAN_LINK = 'href="https://beian.miit.gov.cn/"'
COMMENT_PLUGINS = [
    'giscus', 'twikoo', 'waline', 'utterances', 'cusdis',
    'remark42', 'cactus', 'artalk', 'vssue', 'beaudar',
    'gitalk', 'comentario', 'disqus'
]

results = {
    "compliance_status": "FAILED",
    "beian_id": BEIAN_ID,
    "site_title": "UNKNOWN",
    "checks": {
        "miit_link_valid": False,
        "text_match_valid": False,
        "element_visible": False,
        "interactive_features_detected": False
    },
    "error_message": ""
}

errors = []

print("=" * 50)
print(" ICP 备案合规审计开始")
print("=" * 50)

# ===================================================
# 第一阶段：配置文件静态审计
# ===================================================
print("\n=== 第一阶段：配置文件静态审计 ===\n")

# 1a. 提取网站标题
hugo_toml_path = "config/_default/hugo.toml"
if os.path.exists(hugo_toml_path):
    with open(hugo_toml_path, 'r', encoding='utf-8') as f:
        hugo_content = f.read()
    m = re.search(r'title\s*=\s*"([^"]+)"', hugo_content)
    if m:
        site_title = m.group(1)
        results["site_title"] = site_title
        print(f"  网站标题: {site_title}")
    else:
        print("  [WARN] 无法从 hugo.toml 提取网站标题")
else:
    print(f"  [FAIL] 配置文件不存在: {hugo_toml_path}")
    errors.append("hugo.toml 不存在")

# 1b. 检查评论系统是否禁用
params_toml_path = "config/_default/params.toml"
comments_enabled = None
if os.path.exists(params_toml_path):
    with open(params_toml_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_comments = False
    found_enabled = False
    for line in lines:
        stripped = line.strip()
        if stripped == '[comments]':
            in_comments = True
            continue
        if in_comments and stripped.startswith('[') and stripped != '[comments]':
            in_comments = False
        if in_comments:
            m = re.match(r'^enabled\s*=\s*(true|false)', stripped)
            if m:
                comments_enabled = m.group(1)
                found_enabled = True
                break

    if found_enabled:
        print(f"  评论系统 enabled: {comments_enabled}")
        if comments_enabled == 'false':
            print("  [PASS] 评论系统已彻底禁用 (enabled=false)")
        else:
            print("  [FAIL] 评论系统未禁用！存在交互违规风险")
            errors.append("评论系统未彻底禁用 (enabled=true)")
    else:
        print("  [WARN] 在 params.toml 中未找到 [comments] enabled 配置项")
        errors.append("无法确认评论系统禁用状态")
else:
    print(f"  [FAIL] 配置文件不存在: {params_toml_path}")
    errors.append("params.toml 不存在")

# ===================================================
# 第二阶段：public/index.html 静态断言
# ===================================================
print("\n=== 第二阶段：public/index.html 静态断言 ===\n")

index_path = "public/index.html"
if not os.path.exists(index_path):
    print(f"  [FAIL] {index_path} 不存在！请先执行 hugo --minify")
    errors.append("public/index.html 不存在")
else:
    with open(index_path, 'r', encoding='utf-8', errors='replace') as f:
        index_content = f.read()

    # 2a. 精确链接校验
    # 注意: hugo --minify 会按 HTML5 规范移除非必要引号
    # href="https://beian.miit.gov.cn/" 可能被压缩为 href=https://beian.miit.gov.cn/
    BEIAN_LINK_VARIANTS = [
        'href="https://beian.miit.gov.cn/"',   # 标准带引号
        'href="https://beian.miit.gov.cn"',    # 标准无尾斜杠
        'href=https://beian.miit.gov.cn/',     # minified 无引号带斜杠
        'href=https://beian.miit.gov.cn',      # minified 无引号无斜杠
    ]
    link_found = False
    link_matched = ""
    for variant in BEIAN_LINK_VARIANTS:
        if variant in index_content:
            link_found = True
            link_matched = variant
            break

    if link_found:
        print(f"  [PASS] 工信部链接校验通过")
        print(f"         检测到: {link_matched}")
        results["checks"]["miit_link_valid"] = True
    else:
        print(f"  [FAIL] 未找到工信部链接 (包括 minified 格式)")
        errors.append(f"工信部链接缺失 (检查了引号/无引号两种格式)")

    # 2b. 备案号文本校验
    if BEIAN_ID in index_content:
        print(f"  [PASS] 备案号文本校验通过")
        print(f"         检测到: {BEIAN_ID}")
        results["checks"]["text_match_valid"] = True
    else:
        print(f"  [FAIL] 未找到备案号文本: {BEIAN_ID}")
        errors.append(f"备案号文本缺失 (expected: {BEIAN_ID})")

# ===================================================
# 第三阶段：全站交互插件扫描
# ===================================================
print("\n=== 第三阶段：全站交互功能扫描 ===\n")

html_files = glob.glob("public/**/*.html", recursive=True) + glob.glob("public/*.html")
html_files = list(set(html_files))
print(f"  扫描 HTML 文件数量: {len(html_files)}")

interactive_detected = False
detected_items = []

for plugin in COMMENT_PLUGINS:
    for fpath in html_files:
        try:
            with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if plugin in content:
                rel_path = os.path.relpath(fpath, 'public')
                msg = f"在 {rel_path} 中发现评论插件引用: {plugin}"
                print(f"  [FAIL] 高风险: {msg}")
                detected_items.append(msg)
                interactive_detected = True
                break
        except Exception as e:
            pass

if not interactive_detected:
    print("  [PASS] 全站扫描完毕，未检测到任何交互式评论插件")
else:
    errors.append("检测到高风险互动插件: " + "; ".join(detected_items))

results["checks"]["interactive_features_detected"] = interactive_detected

# ===================================================
# 第四阶段：元素可见性静态推断
# ===================================================
print("\n=== 第四阶段：备案元素可见性静态推断 ===\n")

# 检查页脚模板中备案区域是否有潜在的 CSS 隐藏
footer_path = "layouts/_partials/footer/footer.html"
element_visible_assumption = True  # 静态阶段推断

if os.path.exists(footer_path):
    with open(footer_path, 'r', encoding='utf-8') as f:
        footer_content = f.read()
    
    # 检查 beian section 是否存在
    if 'class="beian"' in footer_content and BEIAN_ID in footer_content:
        print(f"  [PASS] 页脚模板中存在 .beian 节点且包含备案号")
        # 检查是否有内联隐藏样式
        beian_section_match = re.search(r'<section class="beian"[^>]*>(.*?)</section>', footer_content, re.DOTALL)
        if beian_section_match:
            beian_html = beian_section_match.group(0)
            if 'display:none' in beian_html or 'visibility:hidden' in beian_html:
                print("  [FAIL] 检测到内联隐藏样式！")
                element_visible_assumption = False
                errors.append("备案元素存在内联隐藏样式")
            else:
                print("  [PASS] 备案元素无内联隐藏样式")
    else:
        print("  [WARN] 页脚模板中未找到 .beian 节点或备案号")
        element_visible_assumption = False
        errors.append("页脚模板中备案节点缺失")
    
    # 检查 public/index.html 中是否有 beian 节点
    # minify 后 class="beian" 可能变为 class=beian
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8', errors='replace') as f:
            rendered = f.read()
        if 'class="beian"' in rendered or 'class=beian' in rendered:
            print("  [PASS] 编译后 index.html 中存在 .beian 节点 (含 minified 格式)")
            results["checks"]["element_visible"] = True
        else:
            print("  [FAIL] 编译后 index.html 中未找到 .beian 节点")
            results["checks"]["element_visible"] = False
            errors.append("渲染后 HTML 中 .beian 节点不存在")

# ===================================================
# 汇总报告
# ===================================================
print("\n" + "=" * 50)
print(" 审计汇总")
print("=" * 50 + "\n")

if not errors:
    results["compliance_status"] = "PASSED"
    results["error_message"] = ""
    print("  最终状态: PASSED ✓")
else:
    results["compliance_status"] = "FAILED"
    results["error_message"] = "; ".join(errors)
    print("  最终状态: FAILED ✗")
    print(f"  拦截原因: {results['error_message']}")

print()
print("=" * 50)
print(" JSON 审计报告")
print("=" * 50)
json_str = json.dumps(results, ensure_ascii=False, indent=2)
print(json_str)

# 写出报告文件
with open('audit_report.json', 'w', encoding='utf-8') as f:
    f.write(json_str)

print("\n  审计报告已保存至: audit_report.json")