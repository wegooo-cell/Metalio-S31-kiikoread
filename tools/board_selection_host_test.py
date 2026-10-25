#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
"""Exercise board isolation, CMake scope and exported real firmware packages."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import tempfile
import zipfile
import sys

from board_source_view import BOARDS, materialize, select_source
from build_firmware import ROOT, check_image, export, metadata


def reject(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('An invalid board/image/flash plan was accepted')


def source_and_cmake_tests():
    nested = '''#if OTHER
#if KIIKO_BOARD_METALIO47
s31
#else
s3
#endif
#endif
// #if KIIKO_BOARD_METALIO47
const char *s = "#endif";
'''
    assert 's31\n' in select_source(nested, 'metalio47')
    assert 's3\n' in select_source(nested, 'pico')
    assert '#if OTHER' in select_source(nested, 'pico')
    reject(lambda: select_source(nested, 'unknown'))
    reject(lambda: select_source('#if KIIKO_BOARD_METALIO47\n', 'pico'))
    with tempfile.TemporaryDirectory(prefix='kiiko-board-test-') as directory:
        temp = Path(directory)
        cc = shutil.which('cc')
        assert cc, 'Host C compiler required'
        for board in BOARDS:
            info = metadata(board)
            # Real C header must agree with packaging metadata for each compiler flag.
            source = temp / 'identity.c'
            source.write_text('#include <stdio.h>\n#include "kiiko_board_config.h"\n'
                              'int main(void){printf("%s|%s|%u|%s", KIIKO_BOARD_ID,'
                              'KIIKO_BOARD_PROJECT,KIIKO_BOARD_IMAGE_CHIP_ID,'
                              'KIIKO_BOARD_SETTINGS_NAMESPACE);}\n')
            binary = temp / board
            subprocess.run([cc, '-I', str(ROOT / 'main'),
                            '-DKIIKO_BOARD_METALIO47=' + str(int(board == 'metalio47')),
                            str(source), '-o', str(binary)], check=True)
            assert subprocess.check_output([str(binary)], text=True) == '|'.join(map(str,
                [board, info['project'], info['image_chip_id'], info['settings_namespace']]))
            # IDF requirement discovery includes helpers in separate component scopes.
            # 中文：写进 CMake 脚本的路径必须用正斜杠，否则 Windows 盘符路径会被当成转义序列。
            # English: Paths inside generated CMake scripts need forward slashes, or a Windows
            # drive path is parsed as an escape sequence.
            source_root = ROOT.as_posix()
            script = temp / 'board.cmake'
            script.write_text(f'''set(KIIKO_BOARD "{board}")
function(component_scope component source)
  include("{source_root}/cmake/board.cmake")
  kiiko_board_sources(chosen "{source_root}/${{component}}" "${{source}}")
  if(NOT KIIKO_SOURCE_ROOT OR NOT chosen)
    message(FATAL_ERROR "Board scope lost")
  endif()
  if(component STREQUAL "main" AND NOT chosen MATCHES "/boards/{board}/src/main/app_main.c$")
    message(FATAL_ERROR "Wrong board source selected: ${{chosen}}")
  endif()
endfunction()
component_scope("main" "app_main.c")
component_scope("components/ble_page_turner" "src/ble_page_turner.c")
component_scope("main" "app_main.c")
''')
            subprocess.run(['cmake', '-P', str(script)], check=True)
            wrong_target = metadata('metalio47' if board == 'pico' else 'pico')['idf_target']
            result = subprocess.run(['cmake', '-S', str(ROOT), '-B', str(temp / (board + '-wrong-target')),
                                     '-DKIIKO_BOARD=' + board, '-DIDF_TARGET=' + wrong_target],
                                    capture_output=True, text=True)
            assert result.returncode and f"{board} requires {info['idf_target']}" in result.stderr
        script.write_text(f'set(KIIKO_BOARD invalid)\ninclude("{ROOT.as_posix()}/cmake/board.cmake")\n')
        result = subprocess.run(['cmake', '-P', str(script)], capture_output=True, text=True)
        assert result.returncode and 'Unknown KIIKO_BOARD' in result.stderr


def source_view_tests():
    with tempfile.TemporaryDirectory(prefix='kiiko-view-test-') as directory:
        root = Path(directory) / 'source'
        (root / 'main').mkdir(parents=True)
        for board in BOARDS:
            preset = root / 'boards' / board
            preset.mkdir(parents=True)
            (preset / 'dependencies.lock').write_text(board)
        source = root / 'main' / 'example.c'
        original = '#if KIIKO_BOARD_METALIO47\nint s31;\n#else\nint s3;\n#endif\n'
        source.write_text(original)
        output = root / 'scratch' / 'pico'
        materialize(root, output, 'pico')
        target = output / 'main' / 'example.c'
        assert target.read_text() == original  # Production retains real compiler branches.
        os.utime(target, (1, 1))
        source.write_text('int newer;\n')
        os.utime(source, (1, 1))  # Restored old timestamps must still trigger a rebuild.
        materialize(root, output, 'pico')
        assert target.read_text() == 'int newer;\n' and target.stat().st_mtime > 1
        stamp = target.stat().st_mtime_ns
        materialize(root, output, 'pico')
        assert target.stat().st_mtime_ns == stamp  # Unchanged inputs keep incremental builds.
        source.unlink()
        materialize(root, output, 'pico')
        assert not target.exists()  # Removed maintenance files cannot leak into later builds.
        reject(lambda: materialize(root, output, 'metalio47'))
        reject(lambda: materialize(root, root / 'main' / 'generated', 'pico'))


def local_experiment_flags():
    # 真正调用CLI的dry-run，确认缓存里的实验/测试开关不会泄漏进常规构建。
    # Exercise the real CLI dry-run so cached experiment/probe flags cannot leak into normal builds.
    with tempfile.TemporaryDirectory(prefix='kiiko-build-flags-') as directory:
        sdk=Path(directory)
        (sdk/'tools').mkdir();(sdk/'tools/idf.py').write_text('')
        for board in BOARDS:
            (sdk/'components/soc'/metadata(board)['idf_target']).mkdir(parents=True)
            base=[sys.executable,str(ROOT/'tools/build_firmware.py'),'--board',board,
                  '--idf-'+board,str(sdk),'--dry-run']
            plan=json.loads(subprocess.check_output(base,text=True))
            assert '-DMETALIO_PIE_PIXELS=OFF' in plan['command']
            assert '-DMETALIO_LOCAL_LATENCY=OFF' in plan['command']
            assert '-DMETALIO_TEXT_RIPPLE_EXPERIMENT=OFF' in plan['command']
            assert '-DMETALIO_SHELF37_EXPERIMENT=OFF' in plan['command']
            assert '-DMETALIO_LOCAL_TRANSFER_START=OFF' in plan['command']
            if board=='metalio47':
                shelf=json.loads(subprocess.check_output(base+['--s31-shelf37'],text=True))
                assert '-DMETALIO_SHELF37_EXPERIMENT=ON' in shelf['command']
                assert '-DMETALIO_LOCAL_LATENCY=OFF' in shelf['command']
                transfer=json.loads(subprocess.check_output(base+['--s31-transfer-startup-test'],text=True))
                assert '-DMETALIO_LOCAL_TRANSFER_START=ON' in transfer['command']
                assert '-DMETALIO_LOCAL_LATENCY=OFF' in transfer['command']
                plan=json.loads(subprocess.check_output(base+['--s31-pie'],text=True))
                assert '-DMETALIO_PIE_PIXELS=ON' in plan['command']
                assert '-DMETALIO_LOCAL_LATENCY=OFF' in plan['command']
                plan=json.loads(subprocess.check_output(base+['--s31-text-ripple'],text=True))
                assert '-DMETALIO_TEXT_RIPPLE_EXPERIMENT=ON' in plan['command']
                assert '-DMETALIO_LOCAL_LATENCY=OFF' in plan['command']
            else:
                result=subprocess.run(base+['--s31-shelf37'],capture_output=True,text=True)
                assert result.returncode and '--s31-shelf37 requires metalio47 or all' in result.stderr
                rejected=subprocess.run(base+['--s31-transfer-startup-test'],capture_output=True,text=True)
                assert rejected.returncode!=0 and 'requires metalio47 or all' in rejected.stderr
                rejected=subprocess.run(base+['--s31-pie'],capture_output=True,text=True)
                assert rejected.returncode!=0 and 'requires metalio47 or all' in rejected.stderr
                rejected=subprocess.run(base+['--s31-text-ripple'],capture_output=True,text=True)
                assert rejected.returncode!=0 and 'requires metalio47 or all' in rejected.stderr


def real_build_tests(work):
    for board in BOARDS:
        other = BOARDS[1 - BOARDS.index(board)]
        info = metadata(board)
        build = work / board / 'build'
        image = (build / (info['project'] + '.bin')).read_bytes()
        check_image(image, board)
        reject(lambda: check_image(image, other))
        corrupt = bytearray(image)
        struct.pack_into('<H', corrupt, 12, metadata(other)['image_chip_id'])
        reject(lambda: check_image(corrupt, board))
        commands = json.loads((build / 'compile_commands.json').read_text())
        paths = [entry['file'] for entry in commands]
        assert any(f'/boards/{board}/src/main/app_main.c' in path for path in paths)
        assert not any(f'/boards/{other}/src/' in path for path in paths)
        has_hpm = any(path.endswith('/read_pico_flash_hpm.c') for path in paths)
        has_metalio = any('/components/metalio_hw/' in path for path in paths)
        assert has_hpm == (board == 'pico')
        assert has_metalio == (board == 'metalio47')
        for entry in commands:
            if '/main/apps/app_book.c' in entry['file']:
                assert f'-DKIIKO_BOARD_METALIO47={int(board == "metalio47")}' in entry['command']
        with tempfile.TemporaryDirectory(prefix='kiiko-package-test-') as directory:
            package = Path(directory) / board
            result = export(build, package, board)
            assert result['free_app_bytes'] > 0
            assert result['bootloader_offset'] == info['bootloader_offset']
            manifest = json.loads((package / 'manifest.json').read_text())
            parts = manifest['builds'][0]['parts']
            assert {part['path']: part['offset'] for part in parts}['bootloader.bin'] == info['bootloader_offset']
            for part in parts:
                data = (package / part['path']).read_bytes()
                assert len(data) == part['size']
                assert hashlib.sha256(data).hexdigest() == part['sha256']
            assert ('--no-stub' in (package / 'flash-command.txt').read_text()) == (board == 'metalio47')
            archive = package.parent / f"kiikoread-{board}-{info['version']}-USB.zip"
            with zipfile.ZipFile(archive) as zipped:
                assert json.loads(zipped.read('verification.json')) == json.loads(json.dumps(result))
                assert zipped.read('firmware.bin') == image
            # Corrupt an SDK flash plan: no bundle may be exported with a foreign boot offset.
            fake = Path(directory) / 'bad-build'
            fake.mkdir()
            for name in [info['project'] + '.bin', 'bootloader', 'partition_table', 'ota_data_initial.bin']:
                os.symlink(build / name, fake / name)
            plan = json.loads((build / 'flasher_args.json').read_text())
            plan['bootloader']['offset'] = hex(metadata(other)['bootloader_offset'])
            (fake / 'flasher_args.json').write_text(json.dumps(plan))
            reject(lambda: export(fake, Path(directory) / 'invalid', board))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root', type=Path)
    args = parser.parse_args()
    source_and_cmake_tests()
    source_view_tests()
    local_experiment_flags()
    if args.build_root:
        real_build_tests(args.build_root.resolve())
    print('PASS: board identities, CMake component scopes and source selection' +
          ('; both real images, driver isolation, cross-board rejection, flash offsets and ZIP hashes' if args.build_root else ''))
