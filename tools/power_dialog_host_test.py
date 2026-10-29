#!/usr/bin/env python3
"""中文：实际电源识别器与图形边界回归。/ English: Real power input and raster boundary regression.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import re, subprocess, sys, tempfile
from home_cover_cache_host_test import function as source_function
ROOT=Path(__file__).resolve().parents[1]
power=(ROOT/'main/ui/ui_power_dialog.c').read_text()
if len(sys.argv)>2 and sys.argv[1]=='--input-c':
    Path(sys.argv[2]).write_text(power[:power.index('EpdRect ui_power_dialog_rect(void)')].replace('#include "ui_glass.h"\n','').replace('#include "esp_heap_caps.h"\n',''))
    raise SystemExit(0)
def function(path,name):
    return source_function(name,ROOT/path)+'\n'
code=r'''
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <math.h>
#include <limits.h>
#include "ui_power_dialog.h"
#include "ui_kit.h"
#include "ui_image_dither.h"
#define W 684
#define H 1216
static uint8_t fb[W*H/2],before[sizeof(fb)];
static bool text_log;
static int allocations,live_allocations,fail_after=-1,text_calls;
#define MALLOC_CAP_SPIRAM 1
#define MALLOC_CAP_8BIT 2
void *heap_caps_malloc(size_t n,int caps){assert(caps==3&&n<=120000);++allocations;if(fail_after==0)return NULL;if(fail_after>0)--fail_after;void *p=malloc(n);if(p)++live_allocations;return p;}
void heap_caps_free(void *p){if(p){--live_allocations;free(p);}}

void epd_draw_pixel(int x,int y,uint8_t v,uint8_t *p){if(x<0||y<0||x>=W||y>=H)return;size_t at=(size_t)y*W/2+x/2;int shift=(x&1)*4;p[at]=(p[at]&~(15<<shift))|((v>>4)<<shift);}
uint8_t epd_get_pixel(int x,int y,int w,int h,const uint8_t *p){assert(w==W&&h==H&&x>=0&&y>=0&&x<W&&y<H);return ((p[(size_t)y*W/2+x/2]>>((x&1)*4))&15)<<4;}
int epd_width(void){return W;}int epd_height(void){return H;}
int epd_rotated_display_width(void){return W;}int epd_rotated_display_height(void){return H;}
enum EpdRotation epd_get_rotation(void){return EPD_ROT_LANDSCAPE;}
void epd_draw_vline(int x,int y,int h,uint8_t v,uint8_t *p){for(int j=0;j<h;++j)epd_draw_pixel(x,y+j,v,p);}
void epd_draw_hline(int x,int y,int w,uint8_t v,uint8_t *p){for(int i=0;i<w;++i)epd_draw_pixel(x+i,y,v,p);}
void epd_fill_rect(EpdRect r,uint8_t v,uint8_t *p){for(int y=r.y;y<r.y+r.height;++y)for(int x=r.x;x<r.x+r.width;++x)epd_draw_pixel(x,y,v,p);}
void ui_fill_rect_fast(EpdRect r,uint8_t v,uint8_t *p){epd_fill_rect(r,v,p);}
void epd_draw_line(int x,int y,int xx,int yy,uint8_t v,uint8_t *p){assert(x==xx||y==yy);if(x==xx)epd_draw_vline(x,y,yy-y+1,v,p);else epd_draw_hline(x,y,xx-x+1,v,p);}
uint8_t ui_contrast_gray(uint8_t v){return v&0xf0;}
void ui_clear_page(uint8_t *p){memset(p,255,sizeof(fb));}
void ui_text_box(uint8_t *p,EpdRect box,int px,const char *s,enum EpdFontFlags align,bool inverted){(void)p;(void)align;(void)inverted;++text_calls;assert(box.x>=0&&box.y>=0&&box.x+box.width<=W&&box.y+box.height<=H);if(text_log)printf("TEXT %d %d %d %d %d %s\n",box.x,box.y,box.width,box.height,px,s);}
void ui_text(uint8_t *p,int x,int y,int px,const char *s,enum EpdFontFlags align,bool inverted){(void)p;(void)x;(void)y;(void)px;(void)s;(void)align;(void)inverted;}
'''
for name in ('epd_draw_circle','epd_fill_circle_helper','epd_fill_circle'):
    code+=function('components/epdiy/src/epdiy.c',name)
for name in ('ui_read_pixel','icon_nibble','ui_draw_icon','clamp_radius','draw_arc','ui_draw_round_rect','ui_inset_rect','ui_draw_control_frame','ui_fill_round_rect'):
    code+=function('main/ui/ui_kit.c',name)
code+=function('main/ui/ui_image_dither.c','ui_image_dither_gray')
code+=re.sub(r'^#include[^\n]*\n','',(ROOT/'main/ui/ui_glass.c').read_text(),flags=re.M)
code+=re.sub(r'^#include[^\n]*\n','',power,flags=re.M)
code+=r'''
static ui_power_dialog_t dialog;
static cst836u_touch_t touch;
static app_ctx_t ctx;
static EpdRect dirty;
static void sample(int x,int y,int count,bool pressed,bool released){touch=(cst836u_touch_t){.x=x,.y=y,.count=count,.touched=count>0};ctx=(app_ctx_t){.touch=&touch,.now_ms=ctx.now_ms+10,.pressed=pressed,.released=released};}
static ui_power_action_t feed(int x,int y,int count,bool pressed,bool released){sample(x,y,count,pressed,released);return ui_power_dialog_feed(&dialog,&ctx,&dirty);}
static void press(void){assert(feed(UI_POWER_THUMB_X,UI_POWER_THUMB_Y,1,true,false)==UI_POWER_ACTION_NONE&&!dirty.height);}
static void raster_check(void){
 int allocation_count=allocations,labels=text_calls;memcpy(before,fb,sizeof(fb));ui_power_dialog_draw_controls(fb,&dialog,dirty);unsigned changed=0;
 for(int y=0;y<H;++y)for(int x=0;x<W;++x)if(epd_get_pixel(x,y,W,H,fb)!=epd_get_pixel(x,y,W,H,before)){
  ++changed;assert(x>=dirty.x&&x<dirty.x+dirty.width&&y>=dirty.y&&y<dirty.y+dirty.height);
 }
 if(!changed)fprintf(stderr,"unchanged hit=%d pressed=%d position=%d dirty=%d,%d,%d,%d\n",dialog.hit,dialog.pressed,dialog.position,dirty.x,dirty.y,dirty.width,dirty.height);
 assert(changed);assert(allocations==allocation_count&&labels==text_calls);
}
static void glass_checks(void){
 EpdRect r={36,330,612,150};
 memset(fb,255,sizeof(fb));assert(ui_glass_panel(fb,r,75,25,160));
 assert(!live_allocations&&ui_read_pixel(fb,342,405)==12);
 int rim=0;for(int x=120;x<560;++x)rim+=ui_read_pixel(fb,x,332)>12;assert(rim);
 memset(fb,0,sizeof(fb));assert(ui_glass_panel(fb,r,75,25,160));
 assert(!live_allocations&&ui_read_pixel(fb,342,405)==3);
 for(int y=0;y<H;++y)for(int x=0;x<W;++x)epd_draw_pixel(x,y,(x/8&1)?0xf0:0,fb);
 memcpy(before,fb,sizeof(fb));assert(ui_glass_panel(fb,r,75,25,160));
 for(int y=0;y<H;++y)for(int x=0;x<W;++x)
  if(x<r.x||x>=r.x+r.width||y<r.y||y>=r.y+r.height||panel_sdf(x-r.x+.5f,y-r.y+.5f,r.width,r.height,75)>0)
   assert(ui_read_pixel(fb,x,y)==ui_read_pixel(before,x,y));
 int maxstep=0;for(int x=180;x<500;++x){int step=abs(ui_read_pixel(fb,x,405)-ui_read_pixel(fb,x+1,405));if(step>maxstep)maxstep=step;}
 assert(maxstep<10&&!live_allocations);
 memcpy(before,fb,sizeof(fb));fail_after=0;assert(!ui_glass_panel(fb,r,75,25,160));fail_after=-1;
 assert(!memcmp(before,fb,sizeof(fb))&&!live_allocations);
 assert(!ui_glass_panel(fb,(EpdRect){-1,0,40,40},20,25,160));
 assert(!ui_glass_panel(fb,(EpdRect){0,0,W,H},20,25,160));
 assert(!ui_glass_panel(fb,(EpdRect){INT_MAX,0,10,10},20,25,160));
 assert(!memcmp(before,fb,sizeof(fb))&&!live_allocations);
 memset(fb,255,sizeof(fb));
}
int main(int argc,char **argv){
 glass_checks();
 ui_power_dialog_draw(fb,&dialog);press();
 assert(feed(UI_POWER_THUMB_X+1,UI_POWER_THUMB_Y,1,false,false)==UI_POWER_ACTION_NONE&&dialog.position==1);raster_check();
 assert(feed(UI_POWER_THUMB_X+1,UI_POWER_THUMB_Y,1,false,false)==UI_POWER_ACTION_NONE&&!dirty.height);
 for(int pos=2;pos<=UI_POWER_SLIDE_RANGE;++pos){assert(feed(UI_POWER_THUMB_X+pos,UI_POWER_THUMB_Y,1,false,false)==UI_POWER_ACTION_NONE);raster_check();assert(dirty.y>UI_POWER_TRACK_Y&&dirty.y+dirty.height<UI_POWER_TRACK_Y+UI_POWER_TRACK_H);}
 assert(feed(UI_POWER_THUMB_X+UI_POWER_SLIDE_RANGE,UI_POWER_THUMB_Y,0,false,true)==UI_POWER_ACTION_SHUTDOWN);
 assert(feed(UI_POWER_THUMB_X+UI_POWER_SLIDE_RANGE,UI_POWER_THUMB_Y,0,false,true)==UI_POWER_ACTION_NONE);
 ui_power_dialog_reset(&dialog,false);ui_power_dialog_draw(fb,&dialog);
 assert(feed(UI_POWER_THUMB_X+UI_POWER_SLIDE_RANGE,UI_POWER_THUMB_Y,1,true,false)==UI_POWER_ACTION_NONE);
 assert(feed(UI_POWER_THUMB_X+UI_POWER_SLIDE_RANGE,UI_POWER_THUMB_Y,0,false,true)==UI_POWER_ACTION_NONE);
 press();assert(feed(UI_POWER_THUMB_X+UI_POWER_SLIDE_COMMIT-1,UI_POWER_THUMB_Y,1,false,false)==UI_POWER_ACTION_NONE);raster_check();
 assert(feed(500,UI_POWER_THUMB_Y,0,false,true)==UI_POWER_ACTION_NONE&&!dialog.position);raster_check();
 for(int kind=0;kind<5;++kind){
  ui_power_dialog_reset(&dialog,false);press();feed(550,UI_POWER_THUMB_Y,1,false,false);
  if(kind==0)feed(550,UI_POWER_THUMB_Y,2,false,false);
  if(kind==1)feed(550,600,1,false,false);
  if(kind==2){ctx.consumed=true;assert(ui_power_dialog_feed(&dialog,&ctx,&dirty)==UI_POWER_ACTION_NONE);}
  if(kind==3){ctx.touch=NULL;assert(ui_power_dialog_feed(&dialog,&ctx,&dirty)==UI_POWER_ACTION_NONE);}
  if(kind==4){ctx.now_ms=0;assert(ui_power_dialog_feed(&dialog,&ctx,&dirty)==UI_POWER_ACTION_NONE);}
  assert(!dialog.position&&dialog.swallow);assert(feed(555,UI_POWER_THUMB_Y,0,false,true)==UI_POWER_ACTION_NONE);
 }
 ui_power_dialog_reset(&dialog,true);assert(feed(128,374,1,true,false)==UI_POWER_ACTION_NONE);assert(feed(555,374,1,false,false)==UI_POWER_ACTION_NONE);assert(feed(555,374,0,false,true)==UI_POWER_ACTION_NONE);
 for(int i=0;i<2;++i){int x=i?UI_POWER_CANCEL_X:UI_POWER_RESTART_X;
  ui_power_dialog_reset(&dialog,false);ui_power_dialog_draw(fb,&dialog);
  assert(feed(x,UI_POWER_BUTTON_Y,1,true,false)==UI_POWER_ACTION_NONE);raster_check();
  assert(dirty.width==2*UI_POWER_BUTTON_R+3&&dirty.height==dirty.width);
  assert(feed(x,UI_POWER_BUTTON_Y,0,false,true)==(i?UI_POWER_ACTION_CANCEL:UI_POWER_ACTION_RESTART));
  assert(feed(x,UI_POWER_BUTTON_Y,0,false,true)==UI_POWER_ACTION_NONE);
  feed(x-UI_POWER_BUTTON_R+1,UI_POWER_BUTTON_Y-UI_POWER_BUTTON_R+1,1,true,false);assert(feed(x-UI_POWER_BUTTON_R+1,UI_POWER_BUTTON_Y-UI_POWER_BUTTON_R+1,0,false,true)==UI_POWER_ACTION_NONE);
  feed(x,UI_POWER_BUTTON_Y,1,true,false);assert(feed(x+100,UI_POWER_BUTTON_Y,1,false,false)==UI_POWER_ACTION_NONE&&dialog.swallow);assert(feed(x,UI_POWER_BUTTON_Y,0,false,true)==UI_POWER_ACTION_NONE);
 }
 ui_power_dialog_end();assert(!live_allocations);
 // 真底图保留、重复局刷不压深、关闭释放；分配失败仍能取消和关机。
 // Preserve page art, keep repeated feedback stable, free on close, and tolerate allocation failure.
 for(int y=0;y<H;++y)for(int x=0;x<W;++x)epd_draw_pixel(x,y,(uint8_t)(((x/13+y/19)%16)*16),fb);
 memcpy(before,fb,sizeof(fb));ui_power_dialog_reset(&dialog,false);ui_power_dialog_draw(fb,&dialog);
 // Opening must not blur or tint any pixel outside the slider and two button shapes.
 for(int y=0;y<H;y++)for(int x=0;x<W;x++){
  bool inside=false;
  for(int slot=0;slot<3;slot++){
   EpdRect r=slot?power_button_rect(slot):power_track_rect();
   int radius=slot?UI_POWER_BUTTON_R:UI_POWER_TRACK_H/2;
   if(x>=r.x&&y>=r.y&&x<r.x+r.width&&y<r.y+r.height&&
      panel_sdf(x-r.x+.5f,y-r.y+.5f,r.width,r.height,radius)<=0)inside=true;
  }
  if(!inside)assert(ui_read_pixel(fb,x,y)==ui_read_pixel(before,x,y));
 }
 for(int repeat=0;repeat<20;++repeat){
  assert(feed(UI_POWER_RESTART_X,UI_POWER_BUTTON_Y,1,true,false)==UI_POWER_ACTION_NONE);raster_check();
  assert(feed(0,UI_POWER_BUTTON_Y,1,false,false)==UI_POWER_ACTION_NONE);raster_check();
  feed(0,UI_POWER_BUTTON_Y,0,false,true);
 }
 ui_power_dialog_end();assert(!live_allocations);
 fail_after=0;ui_power_dialog_draw(fb,&dialog);assert(!live_allocations);
 assert(feed(UI_POWER_CANCEL_X,UI_POWER_BUTTON_Y,1,true,false)==UI_POWER_ACTION_NONE);
 assert(feed(UI_POWER_CANCEL_X,UI_POWER_BUTTON_Y,0,false,true)==UI_POWER_ACTION_CANCEL);
 ui_power_dialog_end();fail_after=-1;
 puts("PASS: liquid-glass power leaves all pixels outside control shapes unchanged,capture/release, every-pixel drags, cached local raster, allocation/text-free input, repeated feedback, close cleanup and OOM controls");
 if(argc>1){
 FILE *source=argc>2?fopen(argv[2],"rb"):NULL;
 if(source){for(int y=0;y<H;++y)for(int x=0;x<W;++x){int value=fgetc(source);assert(value>=0);epd_draw_pixel(x,y,value,fb);}fclose(source);}
 else memset(fb,255,sizeof(fb));
 ui_power_dialog_reset(&dialog,false);text_log=true;ui_power_dialog_draw(fb,&dialog);
 FILE *file=fopen(argv[1],"wb");assert(file);fprintf(file,"P5\n%d %d\n255\n",W,H);
 for(int y=0;y<H;++y)for(int x=0;x<W;++x)fputc(epd_get_pixel(x,y,W,H,fb)*17/16,file);
 fclose(file);ui_power_dialog_end();assert(!live_allocations);
 }

}
'''
with tempfile.TemporaryDirectory(prefix='kiikoread-power-') as folder:
    c,binary=Path(folder)/'test.c',Path(folder)/'test';c.write_text(code)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined',
        '-I'+str(ROOT/'tools/ui_gesture_stubs'),'-I'+str(ROOT/'main/ui'),str(c),'-lm','-o',str(binary)],check=True)
    subprocess.run([str(binary)]+sys.argv[1:],check=True)
