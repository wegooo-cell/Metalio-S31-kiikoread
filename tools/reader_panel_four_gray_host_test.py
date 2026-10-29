#!/usr/bin/env python3
"""实际四灰面板量化/波形：四方向边界、浅灰底与正文隔离。
Actual four-gray panel targets/LUT: four rotations,crop edges,light fills and body isolation.
"""
from pathlib import Path
import subprocess
import tempfile

root=Path(__file__).resolve().parents[1]
if 'display_reader_panel_gray4_prepare' not in (root/'main/display_reader_waveform.c').read_text():
    print('SKIP: this board has no S31 four-gray panel experiment')
    raise SystemExit(0)
unit=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "display_reader_waveform.h"
#include "metalio_text_ripple.h"
#include "e0470_epaper_waveform.h"
#define W 1216
#define H 684
#define B (W*H/2)
static uint8_t front[B],expected[B],back[B],saved[B];
// 此夹具只验证四灰控件；GL37真实分配由专项测试负责。/ This fixture owns four-gray controls; dedicated tests own real GL37 allocation.
const EpdWaveform* display_reader_panel37_waveform(void){return NULL;}
static enum EpdRotation rotation;
int epd_width(void){return W;}
int epd_height(void){return H;}
enum EpdRotation epd_get_rotation(void){return rotation;}
static void position(int x,int y,int*px,int*py){
 switch(rotation){
 case EPD_ROT_LANDSCAPE:*px=x;*py=y;break;
 case EPD_ROT_PORTRAIT:*px=W-1-y;*py=x;break;
 case EPD_ROT_INVERTED_LANDSCAPE:*px=W-1-x;*py=H-1-y;break;
 default:*px=y;*py=H-1-x;break;
 }
}
static unsigned tone(unsigned v){return v<3?0:v<8?5:v<15?10:15;}
int main(void){
 e0470_waveform_init();
 for(unsigned i=0;i<B;++i)back[i]=saved[i]=(uint8_t)(i*29+3);
 const EpdWaveform *panel=display_reader_panel_gray4_waveform(false);
#if KIIKO_S31_FAST_READER_PANELS
 assert(display_reader_fast_panels_enabled()&&panel&&panel!=metalio_text_ripple_waveform());
 const EpdWaveform *entry=display_reader_panel_gray4_waveform(true);
 assert(entry&&entry!=panel);
 const EpdWaveformPhases *follow=e0470_waveform_phases(&E0470_FOLLOW_WAVEFORM,MODE_DU);
 const EpdWaveformPhases *native=e0470_waveform_phases(&E0470_FULL_WAVEFORM,MODE_DU);
 for(int profile=0;profile<2;++profile){
  const EpdWaveformPhases *p=e0470_waveform_phases(profile?entry:panel,MODE_GL16);
  const int reset=profile?18:8,frames=profile?26:16;
  assert(p&&p->phases==frames&&!p->phase_times);
  for(int from=0;from<16;++from)for(int i=0;i<4;++i){
   int to=i*5,active=0,white=0,black=0;bool rebuild=profile&&(to==5||to==10);
   for(int f=0;f<frames;++f){
    int action=e0470_phase_action(p,f,to,from);if((from==to&&!rebuild)||f>=frames-3)assert(!action);
    active+=action!=0;white+=action==2;black+=action==1;
    int expected=0;
    if(from!=to||rebuild){
     if(rebuild)expected=f<18?e0470_phase_action(native,f,15,0):f<26?e0470_phase_action(follow,f-18,to,15):0;
     else if(to==15){if(f<reset)expected=e0470_phase_action(profile?native:follow,f,15,0);}
     else if(to==0||from==15){if(f<8)expected=e0470_phase_action(follow,f,to,15);}
     else expected=f<reset?e0470_phase_action(profile?native:follow,f,15,0):
          f<reset+8?e0470_phase_action(follow,f-reset,to,15):0;
    }
    assert(action==expected);
   }
   assert((active>0)==(from!=to||rebuild));
   if(from!=to||rebuild){
    if(to==15)assert(white==reset&&!black);
    if(to==0)assert(black==7&&!white);
    if(to==5||to==10)assert(white==(profile?18:from==15?0:reset)&&black==(to==5?5:3));
   }
  }
 }
#else
 assert(!display_reader_fast_panels_enabled()&&!panel&&!display_reader_panel_gray4_waveform(true));
#endif
 for(int rot=0;rot<4;++rot)for(int gray=0;gray<16;++gray){
  rotation=(enum EpdRotation)rot;int lw=(rot&1)?H:W,lh=(rot&1)?W:H;
  const EpdRect areas[]={{19,175,77,140},{-7,-9,60,50},{lw-35,lh-29,60,50}};
  for(unsigned test=0;test<3;++test){
   EpdRect a=areas[test];memset(front,gray*17,B);memcpy(expected,front,B);
   for(int y=a.y;y<a.y+a.height;++y)for(int x=a.x;x<a.x+a.width;++x){
    if(x<0||y<0||x>=lw||y>=lh)continue;
    int px,py;position(x,y,&px,&py);size_t at=(size_t)py*W/2+px/2;unsigned shift=4*(px&1);
    expected[at]=(uint8_t)((expected[at]&~(15u<<shift))|(tone(gray)<<shift));
   }
   assert(display_reader_panel_gray4_prepare(front,a));
   assert(!memcmp(front,expected,B)&&!memcmp(back,saved,B));
   assert(display_reader_panel_gray4_prepare(front,a)&&!memcmp(front,expected,B));
  }
 }
 // 正文速读的原黑白映射保持，不能被面板的四灰策略改变。
 // Preserve the previous text FastBW mapping independently of panel policy.
 EpdiyHighlevelState hl={.front_fb=front,.back_fb=back};rotation=EPD_ROT_LANDSCAPE;
 for(int gray=0;gray<16;++gray){
  memset(front,gray*17,B);assert(display_reader_fast_text_prepare(&hl,(EpdRect){0,0,W,H}));
  for(unsigned i=0;i<B;++i)assert(front[i]==(gray>=8?255:0));
 }
 assert(!display_reader_panel_gray4_prepare(NULL,(EpdRect){0,0,40,40}));
 assert(!display_reader_panel_gray4_prepare(front,(EpdRect){0,0,0,40}));
 assert(!display_reader_panel_gray4_prepare(front,(EpdRect){INT32_MAX,INT32_MAX,INT32_MAX,INT32_MAX}));
 assert(tone(13)==10&&tone(14)==10&&tone(15)==15);
#if KIIKO_S31_FAST_READER_PANELS
 metalio_text_ripple_disable();assert(display_reader_panel_gray4_waveform(false)==panel&&display_reader_panel_gray4_waveform(true)==entry);
#endif
 puts("PASS: real panel4-tone quantizer,192rotation/crop cases,near-white fills retained,body/history isolation,idempotence,text FastBW unchanged;128old/target pairs:unchanged16 feedback,26 entry uniformly resets all midgray targets including5-to5/10-to10/white-origin with18 native white pushes;three final holds/equal-white hold/defaultOFF;body fault independent");
}
'''
with tempfile.TemporaryDirectory(prefix='reader-four-gray-') as temporary:
    folder=Path(temporary);test=folder/'test.c';test.write_text(unit)
    (folder/'esp_log.h').write_text('#define ESP_LOGI(...) ((void)0)\n')
    flags=['cc','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined',
           '-DKIIKO_S31_TEXT_RIPPLE=1','-I'+str(folder),'-Imain','-Itools/waveform_host_stubs',
           '-Icomponents/epdiy/include','-Icomponents/epdiy/src','-Icomponents/e0470_epaper_waveform/include',
           '-Icomponents/e0470_epaper_waveform/metalio']
    sources=[str(test),'main/display_reader_waveform.c','main/metalio_text_ripple.c',
             'components/e0470_epaper_waveform/e0470_epaper_waveform.c',
             'components/e0470_epaper_waveform/e0470_waveform_trim.c']
    for enabled in (0,1):
        exe=folder/('panel-'+str(enabled))
        subprocess.run(flags+['-DKIIKO_S31_FAST_READER_PANELS='+str(enabled),*sources,'-o',str(exe)],cwd=root,check=True)
        subprocess.run([str(exe)],check=True)
