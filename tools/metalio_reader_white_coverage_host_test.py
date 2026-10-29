#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
"""中文：真实S31差分、高层和Moku43相联合验证均匀白底；旧掩码作为反例。
English: Combine actual S31 differences/high-level output/Moku43 phases; retain old dirty masks as a negative control.
"""
from pathlib import Path
import subprocess,tempfile,sys
from home_cover_cache_host_test import function
from test_epd_difference_bounds import PREFIX

ROOT=Path(__file__).resolve().parents[1]
HEADER=r'''#pragma once
#include "epdiy.h"
enum EpdDrawError {EPD_DRAW_SUCCESS,EPD_DRAW_OTHER_ERROR};
typedef struct {uint8_t *front_fb,*back_fb,*difference_fb;bool *dirty_lines;uint8_t *dirty_columns;const EpdWaveform *waveform;} EpdiyHighlevelState;
'''
START=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include "display_reader_waveform.h"
#include "e0470_epaper_waveform.h"
#define MODE_PACKING_1PPB_DIFFERENCE 0x100
#define ESP_LOGI(...) ((void)0)
#define UI_LOCK_WIDTH 684
#define UI_LOCK_HEIGHT 1216
#define W 1216
#define H 684
#define BYTES (W*H/2)
#define _swap_int(a,b) do {int swap_tmp=(a);(a)=(b);(b)=swap_tmp;} while(0)
static enum EpdRotation rotation=EPD_ROT_INVERTED_PORTRAIT;
int epd_height(void){return H;}
enum EpdRotation epd_get_rotation(void){return rotation;}
EpdRect epd_full_screen(void){return (EpdRect){0,0,W,H};}
uint64_t esp_timer_get_time(void){return 0;}
static void hl_record_timing(int a,int b,int c){(void)a;(void)b;(void)c;}
void epd_leading_skip_discard(void){}
void *heap_caps_malloc(size_t n,int caps){assert(caps==3);return malloc(n);}
static _Alignas(16) uint8_t front[BYTES],back[BYTES],saved[BYTES],difference[W*H],columns[W/2];
static bool lines[H];
static EpdiyHighlevelState state={front,back,difference,lines,columns,NULL};
static int draws;static bool fail_draw,expect_full;static unsigned missed_white;

typedef struct {EpdiyHighlevelState *hl;} app_ctx_t;
static unsigned nibble(const uint8_t *p,int x,int y){return (p[y*(W/2)+x/2]>>(4*(x&1)))&15;}
static void set(uint8_t *p,int x,int y,unsigned v){size_t i=(size_t)y*(W/2)+x/2;unsigned shift=4*(x&1);p[i]=(p[i]&~(15u<<shift))|(v<<shift);}
enum EpdDrawError epd_draw_base(EpdRect area,const uint8_t *pixels,EpdRect crop,enum EpdDrawMode mode,
    int temperature,const bool *rows,const uint8_t *cols,const EpdWaveform *wave){
 assert(area.width==W&&area.height==H&&crop.width==W&&crop.height==H);
 assert(mode==(MODE_PACKING_1PPB_DIFFERENCE|MODE_GL16)&&temperature==25&&pixels==difference);
 assert(wave==display_reader_soft_turn_waveform()&&rows==lines&&cols==columns);
 assert(!memcmp(back,saved,BYTES));++draws;missed_white=0;
 const EpdWaveformPhases *ph=e0470_waveform_phases(wave,MODE_GL16);assert(ph&&ph->phases==43);
 int same_white=0;
 for(int f=0;f<43;++f)same_white+=e0470_phase_action(ph,f,15,15)==2;
 assert(same_white==6);
 for(int y=0;y<H;++y)for(int x=0;x<W;++x){
  bool enabled=rows[y]&&((cols[x/2]>>(4*(x&1)))&15);
  unsigned to=nibble(front,x,y),from=nibble(saved,x,y);
  if(expect_full)assert(enabled);
  if(to==15&&!enabled)++missed_white;
  if(enabled)assert(difference[(size_t)y*W+x]==(to<<4|from));
 }
 // 等黑/等灰始终保持；扩大掩码不引入新的黑/灰脉冲。/ Equal black/grays still hold; wider masks introduce no new black/gray pulses.
 for(int v=0;v<15;++v)for(int f=0;f<43;++f)assert(!e0470_phase_action(ph,f,v,v));
 return fail_draw?EPD_DRAW_OTHER_ERROR:EPD_DRAW_SUCCESS;
}
'''
WRAPPERS=r'''
static enum EpdDrawError update_display_area_full_with(EpdiyHighlevelState *hl,const EpdWaveform *wave,enum EpdDrawMode mode,EpdRect area){hl->waveform=wave;return hl_update_area(hl,mode,25,area,true);}
static enum EpdDrawError update_display_area_diff_with(EpdiyHighlevelState *hl,const EpdWaveform *wave,enum EpdDrawMode mode,EpdRect area){hl->waveform=wave;return hl_update_area(hl,mode,25,area,false);}
static void reset(void){
 memset(back,0xff,BYTES);set(back,20,20,0);set(back,31,31,5);set(back,32,32,10);
 for(int y=150;y<500;++y)for(int x=280;x<940;++x)if((x+y)%31==0)set(back,x,y,0);
 memcpy(front,back,BYTES);
 for(int y=180;y<530;++y)for(int x=300;x<980;++x)if((x+y)%29==0)set(front,x,y,(x+y)%15);
 memcpy(saved,back,BYTES);draws=0;fail_draw=false;missed_white=0;
}
int main(void){
 e0470_waveform_init();app_ctx_t ctx={&state};EpdRect full={0,0,H,W};
 // 反例：整页crop仍会跳过页边等白，证明问题是驱动掩码。/ Negative control: full-page crop still omits equal-white margins with dirty-only masks.
 reset();expect_full=false;
 assert(update_display_area_diff_with(&state,display_reader_soft_turn_waveform(),MODE_GL16,full)==EPD_DRAW_SUCCESS);
 assert(draws==1&&missed_white>100000);
 reset();expect_full=true;
 assert(reader_soft_present(&ctx,full)==EPD_DRAW_SUCCESS&&draws==1);
 assert(!missed_white&&!memcmp(front,back,BYTES));
 reset();expect_full=true;memcpy(front,back,BYTES);
 assert(reader_soft_present(&ctx,full)==EPD_DRAW_SUCCESS&&draws==1&&!missed_white);
 reset();expect_full=true;fail_draw=true;
 assert(reader_soft_present(&ctx,full)==EPD_DRAW_OTHER_ERROR&&draws==1&&!missed_white&&!memcmp(back,saved,BYTES));
 reset();expect_full=false;
 assert(reader_soft_present(&ctx,(EpdRect){0,191,H,800})==EPD_DRAW_SUCCESS&&draws==1&&missed_white);
 puts("PASS: real S31 difference/highlevel/Moku43: legacy dirty-mask negative control, uniform full-page6-white coverage, equal black/gray held, one output, unchanged43 phases, image-profile reuse/partial exclusion and failed-scan history");
}
'''
with tempfile.TemporaryDirectory(prefix='s31-reader-white-') as tmp:
 t=Path(tmp);(t/'epd_highlevel.h').write_text(HEADER);(t/'esp_attr.h').write_text('#define IRAM_ATTR\n')
 source=(ROOT/'boards/metalio47/src/components/epdiy/src/render.c').read_text()
 a=source.index('__attribute__((optimize("O3"))) static inline int _interlace_line_unaligned(')
 b=source.index('\nEpdRect epd_difference_image(\n',a)
 prefix=PREFIX.replace('typedef struct {int x,y,width,height;} EpdRect;','')
 hl=ROOT/'components/epdiy/src/highlevel.c'
 functions='\n'.join(function(n,hl) for n in ['_inverse_rotated_area','hl_update_area'])
 wrappers,unit=WRAPPERS.split('static void reset(void)',1)
 c=t/'test.c';c.write_text(START+prefix+source[a:b]+function('epd_difference_image_cropped',ROOT/'boards/metalio47/src/components/epdiy/src/render.c')+functions+wrappers+function('reader_soft_present',ROOT/'main/apps/app_book.c')+'static void reset(void)'+unit)
 flags=['cc','-std=c11','-O1','-Wall','-Wextra','-Werror','-Wno-unknown-attributes','-Wno-pointer-to-int-cast','-fsanitize=address,undefined','-ffunction-sections','-fdata-sections',
  '-Wl,-dead_strip' if sys.platform=='darwin' else '-Wl,--gc-sections','-DKIIKO_BOARD_METALIO47=1','-DKIIKO_S31_READER_PANEL37=1','-DKIIKO_S31_FAST_READER_PANELS=0',
  '-I'+str(t),'-Imain','-Itools/shelf_waveform_host_stubs','-Itools/waveform_host_stubs','-Icomponents/epdiy/include','-Icomponents/epdiy/src','-Icomponents/e0470_epaper_waveform/include','-Icomponents/e0470_epaper_waveform/metalio']
 sources=[str(c),'components/epdiy/src/riscv_pixels.c','boards/metalio47/src/main/display_reader_waveform.c','boards/metalio47/src/main/display_main_waveform.c','boards/metalio47/src/components/e0470_epaper_waveform/e0470_epaper_waveform.c','components/e0470_epaper_waveform/e0470_waveform_trim.c']
 subprocess.run(flags+sources+['-o',str(t/'test')],cwd=ROOT,check=True)
 subprocess.run([str(t/'test')],check=True)
