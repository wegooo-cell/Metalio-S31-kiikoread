#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
"""中文：板级选择层的静态一致性回归。board.json、板级 sdkconfig、分区表、CI 矩阵与文档必须互相对得上，
根目录不得再出现板级配置副本。English: Static consistency checks for the board selection layer; the
board directories stay the single source for identity, config and partitions.
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BOARDS = ROOT / 'boards'
REQUIRED_FILES = ('board.json', 'board.cmake', 'board_hw.c', 'kiiko_board_config.h',
                  'sdkconfig.defaults', 'dependencies.lock')
REQUIRED_KEYS = ('id', 'name', 'idf_target', 'project', 'image_chip_id', 'bootloader_offset',
                 'version', 'sdkconfig', 'partitions', 'settings_namespace', 'online_ota')
VERSION = re.compile(r'^\d+\.\d+\.\d+(?:-[0-9A-Za-z][0-9A-Za-z.]*)?$')
FLASH_SIZES = {'16MB': 16 * 1024 * 1024, '8MB': 8 * 1024 * 1024, '4MB': 4 * 1024 * 1024}


def board_dirs():
    return sorted(path for path in BOARDS.iterdir() if path.is_dir())


def fail(problems, message):
    problems.append(message)


def parse_partitions(path):
    rows = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        fields = [field.strip() for field in line.split(',')]
        assert len(fields) >= 5, f'{path}:{number}: expected at least five columns'
        rows.append({'name': fields[0], 'type': fields[1], 'subtype': fields[2],
                     'offset': int(fields[3], 0), 'size': int(fields[4], 0), 'line': number})
    return rows


def check_partitions(problems, board, info):
    table = board / info['partitions']
    if not table.is_file():
        fail(problems, f'{board.name}: board.json partitions={info["partitions"]} does not exist')
        return
    rows = parse_partitions(table)
    names = [row['name'] for row in rows]
    if len(names) != len(set(names)):
        fail(problems, f'{board.name}: duplicate partition names in {table.name}')
    for required in ('nvs', 'otadata', 'ota_0', 'ota_1', 'storage'):
        if required not in names:
            fail(problems, f'{board.name}: partition table has no {required!r} slot')
    flash = FLASH_SIZES.get(info.get('flash_size', '16MB'), 16 * 1024 * 1024)
    limit = 0
    for row in sorted(rows, key=lambda item: item['offset']):
        if row['offset'] < limit:
            fail(problems, f'{board.name}: {row["name"]} at 0x{row["offset"]:x} overlaps the previous partition')
        limit = row['offset'] + row['size']
    if limit > flash:
        fail(problems, f'{board.name}: partitions end at 0x{limit:x}, beyond {flash // (1024 * 1024)} MiB flash')
    ota = [row for row in rows if row['type'] == 'app']
    if len({row['size'] for row in ota}) > 1:
        fail(problems, f'{board.name}: OTA slots differ in size; rollback needs equal slots')


def check_board(problems, board):
    for name in REQUIRED_FILES:
        if not (board / name).is_file():
            fail(problems, f'{board.name}: missing {name}')
    json_path = board / 'board.json'
    if not json_path.is_file():
        return
    try:
        info = json.loads(json_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as error:
        fail(problems, f'{board.name}: board.json is not valid JSON ({error})')
        return
    missing = [key for key in REQUIRED_KEYS if key not in info]
    if missing:
        fail(problems, f'{board.name}: board.json missing {", ".join(missing)}')
        return
    if info['id'] != board.name:
        fail(problems, f'{board.name}: board.json id is {info["id"]!r}')
    if not str(info['idf_target']).startswith('esp32'):
        fail(problems, f'{board.name}: unexpected idf_target {info["idf_target"]!r}')
    if not VERSION.match(str(info['version'])):
        fail(problems, f'{board.name}: version {info["version"]!r} is not a release version')
    if not isinstance(info['image_chip_id'], int) or not isinstance(info['bootloader_offset'], int):
        fail(problems, f'{board.name}: image_chip_id and bootloader_offset must be integers')
    if not str(info['settings_namespace']).strip():
        fail(problems, f'{board.name}: empty settings_namespace')
    for key in ('sdkconfig', 'partitions'):
        if not (board / str(info[key])).is_file():
            fail(problems, f'{board.name}: {key}={info[key]!r} is not inside the board directory')
    defaults = board / str(info['sdkconfig'])
    if defaults.is_file():
        expected = f'CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="boards/{board.name}/{info["partitions"]}"'
        if expected not in defaults.read_text(encoding='utf-8'):
            fail(problems, f'{board.name}: {defaults.name} must point at {expected.split("=", 1)[1]}')
    check_partitions(problems, board, info)
    return info


def check_root_has_no_board_copies(problems):
    for name in ('sdkconfig.defaults', 'sdkconfig.ci'):
        if (ROOT / name).exists():
            fail(problems, f'root {name} duplicates board config; keep it under boards/<board>/')
    for stray in sorted(ROOT.glob('partitions*.csv')):
        fail(problems, f'root {stray.name} duplicates a board partition table')


def check_ci_matrix(problems, boards):
    workflow = ROOT / '.github/workflows/build.yml'
    if not workflow.is_file():
        return
    text = workflow.read_text(encoding='utf-8')
    matrices = re.findall(r'board:\s*\[([^\]]*)\]', text)
    if not matrices:
        fail(problems, 'CI has no board matrix; the layer would ship untested')
        return
    expected = {board.name for board in boards}
    for entry in matrices:
        listed = {item.strip() for item in entry.split(',') if item.strip()}
        if listed != expected:
            fail(problems, f'CI matrix {sorted(listed)} does not match boards/ {sorted(expected)}')


def check_docs(problems, boards):
    docs = ROOT / 'docs/BOARDS.md'
    if not docs.is_file():
        fail(problems, 'docs/BOARDS.md is missing; the layer needs one place that explains it')
        return
    text = docs.read_text(encoding='utf-8')
    for board in boards:
        if f'`{board.name}`' not in text:
            fail(problems, f'docs/BOARDS.md does not mention board {board.name!r}')


def main():
    problems = []
    if not BOARDS.is_dir():
        print('FAIL: boards/ directory is missing')
        return 1
    boards = board_dirs()
    if not boards:
        print('FAIL: boards/ has no device directory')
        return 1
    infos = {}
    for board in boards:
        info = check_board(problems, board)
        if info:
            infos[board.name] = info
    for key in ('project', 'settings_namespace'):
        values = [info[key] for info in infos.values()]
        duplicated = {value for value in values if values.count(value) > 1}
        if duplicated:
            fail(problems, f'boards share {key}: {sorted(duplicated)}')
    for key in ('image_chip_id', 'bootloader_offset'):
        values = [info[key] for info in infos.values()]
        if len(set(values)) != len(values):
            fail(problems, f'boards share {key}: {values}')
    check_root_has_no_board_copies(problems)
    check_ci_matrix(problems, boards)
    check_docs(problems, boards)
    for problem in problems:
        print(f'FAIL: {problem}')
    if problems:
        return 1
    print(f'PASS: {len(boards)} boards ({", ".join(sorted(infos))}) are self-consistent; '
          'no root duplicates, CI matrix and docs match')
    return 0


if __name__ == '__main__':
    sys.exit(main())
