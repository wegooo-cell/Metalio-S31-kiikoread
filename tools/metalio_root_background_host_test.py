#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
"""中文：真实根页等白维护的预算、缓存隔离与低内存回退。/ English: Real root equal-white budgets, cache separation and low-memory fallback."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
UNIT=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "display_main_waveform.h"
#include "e0470_epaper_waveform.h"
static bool oom;static size_t bytes;static unsigned allocations;
void *heap_caps_malloc(size_t n,int caps){assert(caps==3);if(oom)return NULL;bytes+=n;++allocations;return malloc(n);}
int main(void){
 e0470_waveform_init();
 const EpdWaveform* sources[]={display_du14_white_waveform(),
  display_main_switch_waveform(display_main_water_waveform(),MODE_GL16),
  display_main_switch_waveform(display_main_gray_waveform(),MODE_GL16),
  display_main_switch_waveform(display_main_normal_waveform(),MODE_GL16),
  display_main_switch_waveform(display_main_navigation_waveform(),MODE_GL16)};
 int modes[]={MODE_DU,MODE_GL16,MODE_GL16,MODE_GL16,MODE_GL16};
 const EpdWaveformPhases* native=e0470_waveform_phases(&E0470_FULL_WAVEFORM,MODE_GL16);
 uint8_t saved[48*64];memcpy(saved,native->luts,sizeof(saved));
 oom=true;assert(display_main_background_waveform_with_phases(sources[0],modes[0],6)==sources[0]);oom=false;
 for(unsigned white=6;white<=8;white+=2)for(unsigned i=0;i<5;++i){
  const EpdWaveform *source=sources[i];int mode=modes[i];
  const EpdWaveformPhases* s=e0470_waveform_phases(source,mode);assert(s&&s->phases<=52);
  const EpdWaveform* normal=display_main_clean_waveform_with_phases(source,mode,white);
  const EpdWaveform* background=display_main_background_waveform_with_phases(source,mode,white);
  const EpdWaveformPhases *n=e0470_waveform_phases(normal,mode),*b=e0470_waveform_phases(background,mode);
  assert(normal!=background&&background!=source&&n&&b&&b->phases==s->phases+(int)white+2&&n->phases==b->phases);
  assert(b->phases<=62&&!b->phase_times);
  for(int f=0;f<b->phases;++f)for(int to=0;to<16;++to)for(int from=0;from<16;++from){
   int original=f<s->phases?e0470_phase_action(s,f,to,from):0;
   int want=f<s->phases?original:f<s->phases+(int)white&&to==15?2:0;
   assert(e0470_phase_action(b,f,to,from)==want);
   int old=f<s->phases?original:f<s->phases+(int)white&&to==15&&from!=15?2:0;
   assert(e0470_phase_action(n,f,to,from)==old);
  }
  assert(display_main_background_waveform_with_phases(normal,mode,white)==background);
  assert(display_main_clean_waveform_with_phases(background,mode,white)==normal);
  assert(display_main_background_waveform_with_phases(background,mode,white)==background);
  unsigned count=allocations;size_t size=bytes;
  for(int repeat=0;repeat<100;++repeat)assert(display_main_background_waveform_with_phases(source,mode,white)==background);
  assert(count==allocations&&size==bytes);
 }
 assert(display_main_background_waveform_with_phases(sources[0],modes[0],0)==sources[0]);
 assert(display_main_background_waveform_with_phases(&E0470_FULL_WAVEFORM,MODE_GC16,8)==&E0470_FULL_WAVEFORM);
 assert(display_main_background_waveform_with_phases(&E0470_FOLLOW_WAVEFORM,MODE_DU,6)==&E0470_FOLLOW_WAVEFORM);
 assert(!memcmp(saved,native->luts,sizeof(saved))&&bytes<110000);
 puts("PASS: actual root DU14/gray/water/navigation LUTs: same6/8 budgets plus2holds,all white targets maintained,old normal table unchanged,cross-kind/strength cache isolation,no stacking,warm reuse,bounded memory,OOM and GC/FOLLOW guards");
}
'''
with tempfile.TemporaryDirectory(prefix='s31-root-background-') as temp:
 t=Path(temp);(t/'test.c').write_text(UNIT)
 flags=['cc','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-DKIIKO_BOARD_METALIO47=1','-DKIIKO_S31_MAIN_CLEAN=1','-DKIIKO_S31_DU14=1','-DKIIKO_S31_SHELF37=1',
  '-Imain','-Itools/shelf_waveform_host_stubs','-Itools/waveform_host_stubs','-Icomponents/epdiy/include','-Icomponents/epdiy/src','-Icomponents/e0470_epaper_waveform/include','-Icomponents/e0470_epaper_waveform/metalio']
 files=[str(t/'test.c'),'boards/metalio47/src/main/display_main_waveform.c','boards/metalio47/src/components/e0470_epaper_waveform/e0470_epaper_waveform.c','components/e0470_epaper_waveform/e0470_waveform_trim.c']
 subprocess.run(flags+files+['-o',str(t/'test')],cwd=ROOT,check=True)
 subprocess.run([str(t/'test')],check=True)
