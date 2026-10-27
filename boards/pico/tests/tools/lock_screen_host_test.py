#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# 中文：实际密码锁循环和手势，在取消/错误/多指/低内存/深睡时不能返回页面。
# English: Actual auth loop and gestures cannot release the app on cancel/errors/multitouch/OOM/deep sleep.
from pathlib import Path
import subprocess
import tempfile
from home_cover_cache_host_test import function
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as folder:
 p=Path(folder)
 (p/'app.h').write_text((ROOT/'tools/ui_gesture_stubs/app.h').read_text())
 (p/'epdiy.h').write_text((ROOT/'tools/ui_gesture_stubs/epdiy.h').read_text())
 unit=r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <setjmp.h>
#include <errno.h>
#include <time.h>
#include "ui_pinpad.h"
#define FRAME_BYTES (684u*1216u/2u)
#define UI_LOCK_WIDTH 684
#define UI_LOCK_HEIGHT 1216
#define UI_GRAY_WHITE 255
#define PAD_W 684
#define PAD_H 1216
#define LOW_W 76
#define LOW_H 136
#define RADIUS 72
#define ART_MAGIC UINT32_C(0x50414434)
#define LOCK_SCREEN_CACHE_PARENT "FOLDER"
#define LOCK_ART_PATH LOCK_SCREEN_CACHE_PARENT "/locks/pin-background.bin"
#define MALLOC_CAP_SPIRAM 1
#define MALLOC_CAP_8BIT 2
#define ESP_OK 0
#define EPD_DRAW_SUCCESS 0
#define MODE_GL16 1
#define MODE_DU 2
#define APP_SLEEP_DEEP 0
#define APP_WAKE_KEY 1
#define APP_WAKE_PICKUP 2
#define APP_WAKE_TIMEOUT 3
#define READ_PICO_PMU_KEY_NONE 0
#define pdMS_TO_TICKS(x) (x)
typedef void *cst836u_handle_t;typedef void *sc7a20h_handle_t;typedef int esp_err_t;
typedef struct {int unused;} EpdiyHighlevelState;
typedef int ble_pt_event_t;typedef int ble_pt_raw_t;
typedef struct {uint32_t magic,rotation,style,checksum;uint64_t wallpaper;} art_header_t;
static const int xs[3]={158,342,526},ys[4]={544,703,862,1021},E0470_WAVEFORM=0,E0470_FOLLOW_WAVEFORM=1;
static uint8_t framebuffer[FRAME_BYTES];
static uint8_t selected_style;
static const char *wallpaper="";
uint8_t app_settings_lock_style(void){return selected_style;}
const char *app_settings_wallpaper_path(void){return wallpaper;}
const char *app_settings_bookmark_path(void){return wallpaper;}

static bool fat_semantics;static int rename_calls,rename_fail_at;
static int fat_rename(const char *a,const char *b){
 ++rename_calls;if(rename_fail_at==rename_calls){errno=EIO;return -1;}
 struct stat st;if(fat_semantics && !stat(b,&st)){errno=EEXIST;return -1;}return rename(a,b);
}
#define rename fat_rename
static unsigned stage,idx,waits,verified,ready,held,pushes,fulls,wiped,stops,entries,settles;
static bool enabled_storage=true,valid_storage=true,low_memory,boot_scenario,timeout_scenario,display_failure;
static uint64_t now;
static uint64_t slept_ms;
static uint32_t locked_at=1792886400,wall_unix=1792886400,wake_delay;
static uint8_t s_pin_grace_code_v;
static bool boot_resume;
typedef struct{bool time_synced;uint32_t unix_sec;}pmu_snapshot_t;
static const pmu_snapshot_t*read_pico_pmu_get(void){return NULL;}
static time_t grace_time(time_t*p){time_t v=(time_t)wall_unix+now/1000;if(p)*p=v;return v;}
#define time grace_time
static uint32_t app_settings_pin_locked_at(void){return locked_at;}
static bool pico_boot_has_resume(void){return boot_resume;}

static int power_pending;
static jmp_buf deep;
static struct {int x,y,count,error;} samples[128];static unsigned sample_count;
static void add(int x,int y,int count,int error){samples[sample_count++]=(typeof(samples[0])){x,y,count,error};}
static void tap(int x,int y){add(x,y,1,0);add(x,y,0,0);}
static void correct(void){tap(158,862);tap(526,544);tap(526,862);tap(158,544);}
void lock_pin_wipe(void *bytes,unsigned n){volatile uint8_t *p=bytes;while(n--)*p++=0;++wiped;}
static bool lock_pin_available(void){return valid_storage;}
static bool lock_pin_enabled(void){return valid_storage&&enabled_storage;}
static bool lock_pin_verify(const char pin[5]){++verified;return valid_storage&&!strcmp(pin,"7391");}
static uint8_t *epd_hl_get_framebuffer(EpdiyHighlevelState *h){(void)h;return framebuffer;}
enum EpdRotation epd_get_rotation(void){return 1;}
static void epd_poweron(void){}
void ui_fill_rect_fast(EpdRect r,int gray,uint8_t*fb){assert(r.x==0&&r.y==0&&r.width==684&&r.height==1216);memset(fb,gray,FRAME_BYTES);}

static void epd_poweroff(void){}
static void ui_lock_fallback_draw(uint8_t *fb){memset(fb,255,FRAME_BYTES);fb[FRAME_BYTES/2]=0;}
static size_t heap_caps_get_free_size(int caps){(void)caps;return low_memory?1024*1024:8*1024*1024;}
static void *heap_caps_malloc(size_t n,int caps){(void)caps;return malloc(n);}
static void app_lock_wait_key_idle(int ms){(void)ms;}
static int app_light_sleep_wait_timed(void *acc,unsigned ms){assert(!acc);assert(ms==600000);++waits;now+=wake_delay;slept_ms+=wake_delay;return timeout_scenario?APP_WAKE_TIMEOUT:APP_WAKE_KEY;}
static void app_enter_host_sleep(int mode){assert(mode==APP_SLEEP_DEEP);longjmp(deep,1);}
static int64_t esp_timer_get_time(void){return now*1000;}
static int read_pico_pmu_poll(void){return 0;}
static int read_pico_pmu_take_key_action(void){int action=power_pending;power_pending=0;return action;}
static void read_pico_pmu_drain_events(void){}
static int ble_pt_stop(int ms){assert(ms==2000);++stops;return 0;}
static bool ble_pt_pop_key(ble_pt_event_t *e){(void)e;return false;}
static bool ble_pt_pop_raw(ble_pt_raw_t *e){(void)e;return false;}
static void pico_boot_ready(void){++ready;}
static void pico_boot_hold_resume(void){++held;}
static int cst836u_read(void *tp,cst836u_touch_t *t){(void)tp;if(idx>=sample_count){*t=(cst836u_touch_t){0};return 0;}typeof(samples[0]) s=samples[idx++];*t=(cst836u_touch_t){.touched=s.count!=0,.count=s.count,.x=s.x,.y=s.y};if(s.error<-1){power_pending=-s.error;return ESP_OK;}return s.error;}
static void vTaskDelay(int ms){now+=ms;assert(now-slept_ms<35000||timeout_scenario||!valid_storage);}
static void ui_pinpad_begin(ui_pinpad_t *p,const uint8_t *fb,const char *title){(void)fb;ui_pinpad_end(p);ui_pinpad_reset(p,title,"");if(!low_memory)p->background=malloc(1);}
static void ui_pinpad_paint_input(uint8_t *f,ui_pinpad_t *p){(void)p;f[0]=0xaa;}
static void ui_pinpad_paint(uint8_t *fb,const ui_pinpad_t *p,EpdRect area){(void)p;if(area.y==470)++settles;if(area.y==0&&area.height==1216)++entries;fb[0]=0xaa;}

enum EpdDrawError {EPD_GOOD=0,EPD_BAD=1};
static enum EpdDrawError update_display_area_diff_with(void *h,const int *w,int m,EpdRect a){(void)h;(void)w;(void)a;assert(m==MODE_GL16||m==MODE_DU);++pushes;return display_failure?EPD_BAD:EPD_GOOD;}
static enum EpdDrawError update_display_full(void *h){(void)h;++fulls;return EPD_GOOD;}
static void guard_draw_result(void *h,enum EpdDrawError result){(void)h;(void)result;}
'''.replace('FOLDER',str(p))
 unit+=function('app_settings_pin_grace_minutes',ROOT/'main/settings.c')+'\n'
 unit+=function('lock_pin_grace_active',ROOT/'main/sleep.c')+'\n'
 # Declarations precede the backdrop stub; state/hit logic comes from the production pad.
 unit=unit.replace('static void ui_pinpad_paint_input(', 'void ui_pinpad_paint_input(').replace('static void ui_pinpad_begin(', 'void ui_pinpad_begin(').replace('static void ui_pinpad_paint(', 'void ui_pinpad_paint(')
 for n in ('ui_pinpad_full','ui_pinpad_entry_area','ui_pinpad_end','ui_pinpad_reset','key_rect','joined','hit_test','ui_pinpad_handle'):
  unit+=function(n,ROOT/'main/ui/ui_pinpad.c')+'\n'
 for n in ('checksum','wallpaper_key','lock_screen_restore','lock_screen_save','restore_art','present','present_input','lock_screen_authenticate'):
  unit+=function(n,ROOT/'main/lock_screen.c')+'\n'
 unit+=r'''
static void start(void){idx=sample_count=waits=verified=ready=held=pushes=fulls=entries=settles=0;now=slept_ms=0;wake_delay=0;power_pending=0;memset(framebuffer,0x37,sizeof(framebuffer));add(0,0,0,0);lock_screen_save(framebuffer);}
int main(void){
 EpdiyHighlevelState hl={0};
 // FAT覆盖与提交失败必须保持有效旧图。/ FAT replacement and failed commits must preserve valid old art.
 fat_semantics=true;
 for(selected_style=0;selected_style<4;++selected_style){
  memset(framebuffer,0x11+selected_style,sizeof(framebuffer));assert(lock_screen_save(framebuffer));
  memset(framebuffer,0,sizeof(framebuffer));assert(lock_screen_restore(framebuffer)&&framebuffer[0]==0x11+selected_style);
  rename_calls=0;rename_fail_at=3;memset(framebuffer,0x55,sizeof(framebuffer));assert(!lock_screen_save(framebuffer));
  rename_fail_at=0;memset(framebuffer,0,sizeof(framebuffer));assert(lock_screen_restore(framebuffer)&&framebuffer[0]==0x11+selected_style);
 }
 fat_semantics=false;selected_style=0;
 // 未开启和读取失败均不绘制密码、等待触摸或停蓝牙；读取恢复后已设密码正常验证。
 // Disabled/unreadable settings neither paint a PIN nor wait/stop BLE; a recovered enabled PIN requires verification.
 start();enabled_storage=false;
 lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(!verified&&!entries&&!pushes&&!waits&&!ready&&!held);
 start();enabled_storage=true;valid_storage=false;
 lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(!verified&&!entries&&!pushes&&!waits&&!ready&&!held);
 start();valid_storage=true;correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(verified==1&&entries==1);

 // 实际等待跨过5分钟后必须当次提示密码，不再要求第二次电源键；冷启动不免密。
 // Crossing five minutes prompts on the same wake without a second key; cold starts never use grace.
 const unsigned grace_values[]={0,5,60,480,1440};
 for(unsigned code=0;code<5;++code){s_pin_grace_code_v=code;assert(app_settings_pin_grace_minutes()==grace_values[code]);}
 s_pin_grace_code_v=5;assert(!app_settings_pin_grace_minutes());s_pin_grace_code_v=1;
 const uint32_t waits_ms[]={0,299000,300000,360000,599000};
 for(unsigned i=0;i<sizeof(waits_ms)/sizeof(waits_ms[0]);++i){
  start();wake_delay=waits_ms[i];correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,false);
  assert(waits==1);assert(verified==(waits_ms[i]>=300000));assert(entries==verified);
 }
 start();boot_resume=false;correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(verified==1&&waits==1);
 start();boot_resume=true;wake_delay=299000;correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(!verified&&waits==1&&!entries);
 start();boot_resume=true;wake_delay=360000;correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(verified==1&&waits==1&&entries==1&&ready==1&&held==1);
 start();wall_unix=0;correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,false);assert(verified==1);
 start();wall_unix=locked_at-60;correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,false);assert(verified==1);
 wall_unix=locked_at;boot_resume=false;s_pin_grace_code_v=0;
 // Wrong PIN, cancel, pickup, physical touch buttons, multitouch and read errors, then valid PIN.
 start();for(int i=0;i<4;++i)tap(342,1021);tap(144,1132);add(0,0,0,0);
 tap(342,1350);add(158,544,1,0);add(158,544,2,0);add(158,544,0,0);
 add(158,544,1,0);add(158,544,0,-1);add(0,0,0,0);correct();
 lock_screen_authenticate(&hl,(void*)1,(void*)2,false);assert(verified==2&&waits==2&&!ready&&!held&&wiped>2&&entries==2&&!settles);
 // Cold boot waits for a validated double click, then authenticates and retains resume.
 start();correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(verified==1&&waits==1&&ready==1&&held==1&&entries==1&&!settles);
 // PMU short/long actions only return to the locked art, then demand authentication again.
 for(int action=2;action<=3;++action){start();add(0,0,0,-action);for(int i=0;i<10;++i)add(0,0,0,0);correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(verified==1&&waits==2);}
 // Low-memory/cache fallback and display errors still demand the correct credential.
 start();low_memory=display_failure=true;correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(verified==1&&fulls>0);low_memory=display_failure=false;
 start();low_memory=true;correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,false);assert(verified==1&&waits==1&&entries==1&&!settles);low_memory=false;
 // 单次密码入场失败重建同一画面；不能绕过验证。
 // A failed single entry rebuilds the protected PIN screen; verification remains mandatory.
 start();display_failure=true;correct();lock_screen_authenticate(&hl,(void*)1,(void*)2,false);assert(verified==1&&entries==1&&!settles&&fulls>0);display_failure=false;
 // Cancel never releases the caller: deep sleep terminates the protected loop instead.
 start();tap(144,1132);timeout_scenario=true;if(!setjmp(deep)){lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(0);}assert(!verified&&waits==1);timeout_scenario=false;
 // 按用户选择，持续不可读状态直接返回，不显示虚假的四位密码。
 // User-selected unreadable storage returns immediately without a spurious four-digit prompt.
 start();correct();valid_storage=false;lock_screen_authenticate(&hl,(void*)1,(void*)2,true);assert(!verified&&!entries&&!waits&&!pushes);valid_storage=true;
 uint8_t *f=malloc(FRAME_BYTES);assert(lock_screen_restore(f));
 // 旧拼贴缓存不能跨样式进入票根或壁纸。/ Collage art must not cross into ticket or wallpaper mode.
 for(unsigned saved=0;saved<3;++saved){
  selected_style=saved;lock_screen_save(framebuffer);
  for(unsigned current=0;current<3;++current){selected_style=current;memset(f,0xee,FRAME_BYTES);assert(lock_screen_restore(f)==(current==saved));if(current!=saved)assert(f[0]==0xee);}
 }
 selected_style=2;lock_screen_save(framebuffer);assert(lock_screen_restore(f));
 selected_style=0;memset(f,0xee,FRAME_BYTES);assert(!lock_screen_restore(f)&&f[0]==0xee);
 selected_style=1;assert(!lock_screen_restore(f));
 wallpaper=LOCK_SCREEN_CACHE_PARENT "/a.jpg";lock_screen_save(framebuffer);assert(lock_screen_restore(f));
 wallpaper=LOCK_SCREEN_CACHE_PARENT "/b.jpg";memset(f,0xee,FRAME_BYTES);assert(!lock_screen_restore(f)&&f[0]==0xee);
 lock_screen_save(framebuffer);assert(lock_screen_restore(f));
 FILE *image=fopen(wallpaper,"wb");assert(image);assert(fputs("new image",image)>=0&&fclose(image)==0);
 assert(!lock_screen_restore(f));lock_screen_save(framebuffer);assert(lock_screen_restore(f));
 image=fopen(wallpaper,"ab");assert(image);assert(fputc(1,image)!=EOF&&fclose(image)==0);assert(!lock_screen_restore(f));
 assert(remove(wallpaper)==0);lock_screen_save(framebuffer);assert(lock_screen_restore(f));
 assert(!lock_screen_restore(NULL));
 // 新兜底规则不能继续复用旧版完整缓存；当前有效缓存仍直接恢复。
 // Reject a complete old-policy cache while retaining valid current-generation art.
 lock_screen_save(framebuffer);FILE *policy=fopen(LOCK_ART_PATH,"r+b");assert(policy);
 uint32_t old_policy=UINT32_C(0x50414432);assert(fwrite(&old_policy,1,4,policy)==4&&!fclose(policy));
 memset(f,0xee,FRAME_BYTES);assert(!lock_screen_restore(f)&&f[0]==0xee);
 restore_art(f,NULL);assert(f[0]==255&&f[FRAME_BYTES/2]==0);
 lock_screen_save(framebuffer);assert(lock_screen_restore(f));
 // 旧版缓存必须重绘当前样式，旋转不符也不能复用。/ Old cache versions and mismatched rotations require current-style redraw.
 FILE *old=fopen(LOCK_ART_PATH,"wb");assert(old);uint32_t legacy[3]={UINT32_C(0x50414431),1,checksum(framebuffer)};
 assert(fwrite(legacy,1,sizeof(legacy),old)==sizeof(legacy)&&fwrite(framebuffer,1,FRAME_BYTES,old)==FRAME_BYTES&&fclose(old)==0);
 assert(!lock_screen_restore(f));
 selected_style=0;lock_screen_save(framebuffer);FILE *rotated=fopen(LOCK_ART_PATH,"r+b");assert(rotated);
 uint32_t rotation=2;assert(fseek(rotated,4,SEEK_SET)==0&&fwrite(&rotation,1,sizeof(rotation),rotated)==sizeof(rotation)&&fclose(rotated)==0);assert(!lock_screen_restore(f));
 selected_style=0;lock_screen_save(framebuffer);assert(lock_screen_restore(f));FILE *bad=fopen(LOCK_ART_PATH,"r+b");assert(bad);fputc(0,bad);fclose(bad);assert(!lock_screen_restore(f));free(f);
 assert(stops>=5);puts("PASS: grace rechecked after wake at0/299/300/360/599s,deep-resume deadline,cold start,invalid/rollback clock,default-off; actual exclusive auth loop blocks wrong/cancel/touch keys/pickup/multitouch/read faults; cold boot holds resume; OOM/display errors fail closed; cancel/idle deep-sleep; read faults follow the nonblocking policy; normal PIN and cached-art validation retained");
}
'''
 (p/'test.c').write_text(unit)
 subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-variable','-fsanitize=address,undefined','-I'+str(p),'-I'+str(ROOT/'main/ui'),'-I'+str(ROOT/'main/font'),'-I'+str(ROOT/'main'),str(p/'test.c'),str(ROOT/'main/ui/ui_gesture.c'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
