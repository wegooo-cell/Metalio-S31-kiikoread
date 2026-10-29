#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
"""中文：S31原始DU14逐像素迁移、路由与灰阶隔离的实际C回归。
English: Exercise actual S31 DU14 transitions, routing and unchanged gray profiles.
"""
from pathlib import Path
import hashlib
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
provided=ROOT/'boards/metalio47/src/components/e0470_epaper_waveform/my_waveform_du14.h'
assert hashlib.sha256(provided.read_bytes()).hexdigest()=='cac0efbcb2801114b36a4bee5eaa9c453dcd7d098210ef2739f853e86a0c39f4'
unit=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include "display_reader_waveform.h"
#include "display_main_waveform.h"
#include "e0470_epaper_waveform.h"
static unsigned allocations;
void *heap_caps_malloc(size_t n,int caps){assert(caps==3);++allocations;return malloc(n);}
int epd_width(void){return 1216;}
int epd_height(void){return 684;}
enum EpdRotation epd_get_rotation(void){return EPD_ROT_INVERTED_PORTRAIT;}
static void dump(FILE *file,const EpdWaveform *wave,int mode){
 const EpdWaveformPhases *p=e0470_waveform_phases(wave,mode);
 assert(p&&p->luts&&!p->phase_times);
 assert(fwrite(&p->phases,sizeof(p->phases),1,file)==1);
 assert(fwrite(p->luts,64,p->phases,file)==(size_t)p->phases);
}
int main(int argc,char **argv){
 assert(argc==2);e0470_waveform_init();
 unsigned before=allocations;
 const EpdWaveform *fast=display_reader_fast_text_waveform();
 const EpdWaveformPhases *text=e0470_waveform_phases(fast,MODE_GL16);
 const EpdWaveform *bw=display_main_bw_waveform(),*page=display_main_page_bw_waveform();
#if KIIKO_S31_DU14
 const EpdWaveform *raw=e0470_du14_waveform();assert(raw&&raw==bw&&raw==page&&allocations==before);
 const EpdWaveformPhases *p=e0470_waveform_phases(raw,MODE_DU);
 assert(text&&p&&text->phases==18&&text->luts!=p->luts&&p->phases==14&&!p->phase_times);
 assert(raw->num_modes==1&&raw->num_temp_ranges==1&&raw->temp_intervals[0].min==0&&raw->temp_intervals[0].max==50);
 for(int f=0;f<14;++f)for(int to=0;to<16;++to)for(int from=0;from<16;++from){
  int want=to==from?(to==0&&f>=10?1:0):to<8?(f<13?1:0):2;
  assert(e0470_phase_action(p,f,to,from)==want);
 }
 assert(display_main_switch_waveform(raw,MODE_DU)==raw); // 原14相不暗中加补帧。/ No hidden extra phases.
 assert(display_main_shelf_exit_waveform()==raw);
 const EpdWaveformPhases *turn=e0470_waveform_phases(display_main_bw_turn_waveform(),MODE_GL16);
 assert(turn&&turn->luts==p->luts&&turn->phases==14);
#else
 (void)before;assert(!e0470_du14_waveform()&&text&&text->phases==24);
 assert(e0470_waveform_phases(bw,MODE_DU)->phases==20&&e0470_waveform_phases(page,MODE_DU)->phases==20);
#endif
 FILE *file=fopen(argv[1],"wb");assert(file);
 // 默认灰阶、普通/图片/底栏合成、面板4灰和全刷逐字节跨构建比对。
 // Compare default gray, normal/image/footer synthesis, four-gray panels and full refresh across both builds.
 dump(file,&E0470_FULL_WAVEFORM,MODE_DU);dump(file,&E0470_FULL_WAVEFORM,MODE_GC16);dump(file,&E0470_FULL_WAVEFORM,MODE_GL16);
 dump(file,&E0470_WAVEFORM,MODE_DU);dump(file,&E0470_WAVEFORM,MODE_GL16);
 dump(file,&E0470_FOLLOW_WAVEFORM,MODE_DU);dump(file,display_reader_text_waveform(),MODE_GL16);
 dump(file,display_main_normal_waveform(),MODE_GL16);dump(file,display_main_gray_waveform(),MODE_GL16);
 dump(file,display_main_navigation_waveform(),MODE_GL16);
 dump(file,display_main_shelf37_waveform(false),MODE_GL16);dump(file,display_main_shelf37_waveform(true),MODE_GL16);
 dump(file,display_reader_panel37_waveform(),MODE_GL16);
 dump(file,display_reader_panel_gray4_waveform(false),MODE_GL16);dump(file,display_reader_panel_gray4_waveform(true),MODE_GL16);
 assert(!fclose(file));
 puts("PASS: DU14 routing/3584 transitions, no implicit extra phases or DU14 heap, raw/full/grayscale profiles isolated");
}
'''
with tempfile.TemporaryDirectory(prefix='kiiko-s31-du14-') as folder:
    t=Path(folder);(t/'test.c').write_text(unit)
    (t/'epd_internals.h').write_text('#include "epd_waveform.h"\n')
    flags=['cc','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',
           '-DKIIKO_BOARD_METALIO47=1','-DKIIKO_S31_SHELF37=1','-DKIIKO_S31_READER_PANEL37=1','-DKIIKO_S31_FAST_READER_PANELS=1',
           '-I'+str(t),'-Imain','-Itools/shelf_waveform_host_stubs','-Itools/waveform_host_stubs',
           '-Icomponents/epdiy/include','-Icomponents/epdiy/src','-Icomponents/e0470_epaper_waveform/include',
           '-Icomponents/e0470_epaper_waveform/metalio']
    files=[str(t/'test.c'),'boards/metalio47/src/main/display_main_waveform.c','boards/metalio47/src/main/display_reader_waveform.c',
           'boards/metalio47/src/components/e0470_epaper_waveform/e0470_epaper_waveform.c','components/e0470_epaper_waveform/e0470_waveform_trim.c']
    profiles=[]
    for enabled in (0,1):
        exe=t/f'test-{enabled}';output=t/f'profiles-{enabled}'
        subprocess.run(flags+[f'-DKIIKO_S31_DU14={enabled}',*files,'-o',str(exe)],cwd=ROOT,check=True)
        subprocess.run([str(exe),str(output)],check=True)
        profiles.append(output.read_bytes())
    assert profiles[0]==profiles[1]
    print('PASS: 15 native/gray profiles byte-identical with DU14 OFF/ON; SHA256',hashlib.sha256(profiles[0]).hexdigest())
