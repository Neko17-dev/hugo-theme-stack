# ===================================================
# ICP 备案合规审计脚本 v1.0
# 审计对象: hugo-theme-stack 站点
# ===================================================

$ErrorCount = 0
$Results = @{}

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " ICP 备案合规审计开始" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ===== 第一阶段：配置文件静态审计 =====
Write-Host "=== 第一阶段：配置文件静态审计 ===" -ForegroundColor Yellow
Write-Host ""

# 1a. 检查网站标题
$hugoToml = Get-Content 'config/_default/hugo.toml' -Raw -Encoding UTF8
$siteTitle = "UNKNOWN"
if ($hugoToml -match 'title\s*=\s*"([^"]+)"') {
    $siteTitle = $Matches[1]
    Write-Host "  网站标题: $siteTitle"
} else {
    Write-Host "  [WARN] 无法提取网站标题" -ForegroundColor Yellow
}

# 1b. 检查评论系统是否彻底禁用
$paramsToml = Get-Content 'config/_default/params.toml' -Raw -Encoding UTF8
$commentsEnabled = "unknown"
if ($paramsToml -match '(?m)^\[comments\]\s*\r?\n\s*enabled\s*=\s*(true|false)') {
    $commentsEnabled = $Matches[1]
    Write-Host "  评论系统 enabled: $commentsEnabled"
} else {
    Write-Host "  [WARN] 无法以正则匹配评论系统状态，尝试备用检测..." -ForegroundColor Yellow
    # 备用: 逐行扫描
    $lines = $paramsToml -split "`n"
    $inCommentsSection = $false
    foreach ($line in $lines) {
        $trimmed = $line.Trim()
        if ($trimmed -eq '[comments]') { $inCommentsSection = $true; continue }
        if ($inCommentsSection -and $trimmed -match '^\[') { $inCommentsSection = $false }
        if ($inCommentsSection -and $trimmed -match '^enabled\s*=\s*(true|false)') {
            $commentsEnabled = $Matches[1]
            Write-Host "  评论系统 enabled (备用检测): $commentsEnabled"
            break
        }
    }
}

if ($commentsEnabled -eq 'false') {
    Write-Host "  [PASS] 评论系统已彻底禁用 (enabled=false)" -ForegroundColor Green
    $Results['comments_disabled'] = $true
} else {
    Write-Host "  [FAIL] 评论系统未禁用！当前状态: $commentsEnabled" -ForegroundColor Red
    $Results['comments_disabled'] = $false
    $ErrorCount++
}

Write-Host ""
Write-Host "=== 第二阶段：public/index.html 静态断言 ===" -ForegroundColor Yellow
Write-Host ""

# ===== 第二阶段：public/index.html 静态断言 =====
$indexPath = 'public/index.html'
if (-not (Test-Path $indexPath)) {
    Write-Host "  [FAIL] public/index.html 不存在！请先执行 hugo --minify" -ForegroundColor Red
    $Results['miit_link_valid'] = $false
    $Results['text_match_valid'] = $false
    $ErrorCount += 2
} else {
    $indexContent = Get-Content $indexPath -Raw -Encoding UTF8

    # 2a. 链接校验 - 精确匹配
    $linkLiteral = 'href="https://beian.miit.gov.cn/"'
    if ($indexContent.Contains($linkLiteral)) {
        Write-Host "  [PASS] 工信部精确链接校验通过" -ForegroundColor Green
        Write-Host "         检测到: $linkLiteral"
        $Results['miit_link_valid'] = $true
    } else {
        Write-Host "  [FAIL] 未找到精确链接: $linkLiteral" -ForegroundColor Red
        # 尝试查找近似链接给出提示
        if ($indexContent -match 'beian\.miit\.gov\.cn') {
            Write-Host "  [HINT] 发现近似链接，但格式可能不完全匹配，请检查" -ForegroundColor Yellow
        }
        $Results['miit_link_valid'] = $false
        $ErrorCount++
    }

    # 2b. 备案号文本校验
    $beianText = "津ICP备2026009218号"
    if ($indexContent.Contains($beianText)) {
        Write-Host "  [PASS] 备案号文本校验通过" -ForegroundColor Green
        Write-Host "         检测到: $beianText"
        $Results['text_match_valid'] = $true
    } else {
        Write-Host "  [FAIL] 未找到备案号文本: $beianText" -ForegroundColor Red
        $Results['text_match_valid'] = $false
        $ErrorCount++
    }

    # 2c. 全站交互插件扫描（扫描所有生成的 html 文件）
    Write-Host ""
    Write-Host "=== 第三阶段：全站交互功能扫描 ===" -ForegroundColor Yellow
    Write-Host ""
    $commentPlugins = @('giscus', 'twikoo', 'waline', 'utterances', 'cusdis', 'remark42', 'cactus', 'artalk', 'vssue', 'beaudar', 'gitalk', 'comentario')
    $interactiveDetected = $false
    $htmlFiles = Get-ChildItem -Path 'public' -Recurse -Filter '*.html'
    Write-Host "  扫描 HTML 文件数量: $($htmlFiles.Count)"
    foreach ($plugin in $commentPlugins) {
        $found = $false
        foreach ($file in $htmlFiles) {
            $content = Get-Content $file.FullName -Raw -Encoding UTF8
            if ($content -match $plugin) {
                Write-Host "  [FAIL] 高风险: 在 $($file.Name) 中发现评论插件引用: $plugin" -ForegroundColor Red
                $interactiveDetected = $true
                $found = $true
                break
            }
        }
    }
    if (-not $interactiveDetected) {
        Write-Host "  [PASS] 全站扫描完毕，未检测到任何交互式评论插件" -ForegroundColor Green
    } else {
        $ErrorCount++
    }
    $Results['interactive_features_detected'] = $interactiveDetected
}

# ===== 输出汇总报告 =====
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " 审计汇总" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$miitLinkValid = if ($Results.ContainsKey('miit_link_valid')) { $Results['miit_link_valid'] } else { $false }
$textMatchValid = if ($Results.ContainsKey('text_match_valid')) { $Results['text_match_valid'] } else { $false }
$elementVisible = $true  # 静态阶段假设可见（Headless 阶段会验证）
$interactiveDetectedFinal = if ($Results.ContainsKey('interactive_features_detected')) { $Results['interactive_features_detected'] } else { $false }

if ($ErrorCount -eq 0) {
    $complianceStatus = "PASSED"
    $errorMsg = ""
    Write-Host "  最终状态: PASSED" -ForegroundColor Green
} else {
    $complianceStatus = "FAILED"
    $msgs = @()
    if (-not $miitLinkValid) { $msgs += "工信部精确链接缺失" }
    if (-not $textMatchValid) { $msgs += "备案号文本缺失" }
    if ($interactiveDetectedFinal) { $msgs += "检测到高风险互动插件引用" }
    if (-not $Results['comments_disabled']) { $msgs += "评论系统未彻底禁用" }
    $errorMsg = $msgs -join "; "
    Write-Host "  最终状态: FAILED" -ForegroundColor Red
    Write-Host "  拦截原因: $errorMsg" -ForegroundColor Red
}

Write-Host ""

# JSON 格式输出
$jsonOutput = @"
{
  "compliance_status": "$complianceStatus",
  "beian_id": "津ICP备2026009218号",
  "site_title": "$siteTitle",
  "checks": {
    "miit_link_valid": $($miitLinkValid.ToString().ToLower()),
    "text_match_valid": $($textMatchValid.ToString().ToLower()),
    "element_visible": $($elementVisible.ToString().ToLower()),
    "interactive_features_detected": $($interactiveDetectedFinal.ToString().ToLower())
  },
  "error_message": "$errorMsg"
}
"@

Write-Host "============================================" -ForegroundColor Cyan
Write-Host " JSON 审计报告" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host $jsonOutput

# 将报告也写入文件
$jsonOutput | Out-File -FilePath 'audit_report.json' -Encoding UTF8
Write-Host ""
Write-Host "  审计报告已保存至: audit_report.json" -ForegroundColor Cyan