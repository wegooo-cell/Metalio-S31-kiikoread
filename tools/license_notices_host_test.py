#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
"""中文：许可证缺口回归测试。受版本管理的源码与文档里 `licenses/<名>.txt` 的引用必须逐字存在；官网
链接要么在 flash/licenses/ 里，要么由 tools/stage_public_flash.py 生成。漏一个文件就是分发时缺声明。
English: License-notice regression test. Every `licenses/<name>.txt` reference in tracked text must
exist with exact case, and every website link must come from flash/licenses/ or the staging map; a
missing file would ship a binary without the notice it owes.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
# 中文：只认仓库内路径，排除 URL（前面是 /）和更长的相对路径。
# English: Repository paths only; a URL or a deeper path prefix must not match.
REFERENCE = re.compile(r'(?<![\w./:-])(?:\.\./)*(?:flash/)?licenses/[A-Za-z0-9._-]+\.(?:txt|md)')
PAGE_LINK = re.compile(r'href="\./licenses/([^"]+)"')
# 中文：随站点分发的页面；其他本地链接由 staging 自己校验。
# English: Pages the site serves; staging validates every other local link itself.
PAGES = ('flash/index.html', 'flash/notices.html', 'flash/manual.html',
         'flash/manual/index.html', 'flash/metalio/index.html')


def exists_exact(path: Path) -> bool:
    # 中文：Windows 大小写不敏感，必须逐项比对，否则会重现 METALIO/Metalio 这种断链。
    # English: Windows is case-insensitive, so compare directory entries one by one.
    return path.is_file() and path.name in {entry.name for entry in path.parent.iterdir()}


def reference_files() -> list[Path]:
    files = [ROOT / 'THIRD_PARTY_NOTICES.md', ROOT / 'LICENSE']
    files += sorted(ROOT.glob('README*.md'))
    files += sorted(p for p in (ROOT / 'docs').rglob('*.md') if 'local' not in p.parts)
    files += sorted(p for p in (ROOT / 'components').rglob('*') if p.name.startswith('LICENSE'))
    return [path for path in dict.fromkeys(files) if path.is_file()]


def staged_names() -> set[str]:
    script = (ROOT / 'tools/stage_public_flash.py').read_text(encoding='utf-8')
    return set(re.findall(r'"([A-Za-z0-9._-]+\.txt)"', script))


def main() -> int:
    problems: list[str] = []

    for page in reference_files():
        text = page.read_text(encoding='utf-8', errors='replace')
        for match in REFERENCE.finditer(text):
            target = (page.parent / match.group(0)).resolve()
            if not exists_exact(target):
                problems.append(f'{page.relative_to(ROOT)}: missing {match.group(0)}')

    shipped = staged_names()
    for page in PAGES:
        path = ROOT / page
        if not path.is_file():
            continue
        for name in PAGE_LINK.findall(path.read_text(encoding='utf-8')):
            if not (ROOT / 'flash/licenses' / name).is_file() and name not in shipped:
                problems.append(f'{page}: ./licenses/{name} is neither in flash/licenses nor staged')

    for problem in problems:
        print(f'FAIL: {problem}')
    if problems:
        return 1
    print(f'PASS: {len(reference_files())} files reference only existing notices; '
          f'{len(shipped)} staged license files cover every website link')
    return 0


if __name__ == '__main__':
    sys.exit(main())
