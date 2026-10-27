#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Execute S31 lock entry/PNG/reference/PIN paths, preserving retained-sleep semantics."""
from pathlib import Path
import subprocess,tempfile
from home_cover_cache_host_test import function
r=Path(__file__).resolve().parents[1]
u=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define FRAME_BYTES (684u*1216u/2u)
#define ESP_OK 0
#define ESP_ERR_NOT_FINISHED 1
#define APP_LOCK_IGNORE_BOOT_MS 1000
#define ESP_LOGI(...) ((void)0)
#define ESP_LOGW(...) ((void)0)
#define pdMS_TO_TICKS(x) (x)
enum EpdDrawError{EPD_DRAW_SUCCESS,EPD_DRAW_FAULT};
typedef struct{uint8_t*back_fb;}EpdiyHighlevelState;
typedef void *sc7a20h_handle_t;typedef void*cst836u_handle_t;
typedef struct{bool mounted;}read_pico_sd_info_t;
typedef struct{bool active;}app_lock_font_t;
static uint8_t pixels[FRAME_BYTES],panel[FRAME_BYTES],style,background=0x32;
static bool pin,decode_ok=true,transfer_ok=true,ble_ok=true,output_ok=true,white_ok=true,boot_cache,cache_ok,system_binary;
static unsigned old_style,draws[4],presents,outputs,auths,begins,ends,resumes,cleared,waits,saves,lamp_off,lamp_restore,white_outputs,white_faults,image_clears;
static bool s_lock_feedback_started,s_lock_deep_ready,s_lock_frame_cached,s_boot_lock_draw,s_boot_power_on,s_boot_power_wake;
static void lock_resume_service(void){}
static bool app_lock_resume_frame(void*h){(void)h;return false;}
static cst836u_handle_t s_lock_sleep_touch;
static unsigned media_resumes;
static int lock_resume_media_io(uint32_t wait_ms){assert(!wait_ms&&!s_lock_sleep_touch);++media_resumes;return ESP_OK;}
static uint8_t app_settings_lock_style(void){return style;}
static const char*app_settings_wallpaper_path(void){return "/sdcard/wall.jpg";}
static const char*app_settings_bookmark_path(void){return "/sdcard/overlay.png";}
static bool lock_pin_enabled(void){return pin;}
static bool art(unsigned id,uint8_t*f){assert(id==style);if(id==3)assert(f[0]==(boot_cache?255:background));if(id==1&&!boot_cache)assert(!white_outputs&&panel[0]==background);++draws[id];memset(f,0x10+id,FRAME_BYTES);return decode_ok;}
static bool book_ticket_draw(uint8_t*f,bool reader){(void)reader;return art(0,f);}
static bool ui_wallpaper_prepare_lock(uint8_t*f,const char*p){assert(!strcmp(p,app_settings_wallpaper_path()));return art(1,f);}
static bool book_lock_collage_prepare(uint8_t*f){return art(2,f);}
static bool book_lock_bookmark_draw(uint8_t*f,const char*p){assert(!strcmp(p,app_settings_bookmark_path()));return art(3,f);}
static void ui_wallpaper_cache_commit(const uint8_t*f){assert(style==1&&presents==1&&!memcmp(f,panel,FRAME_BYTES));}
static void book_lock_collage_cache_commit(const uint8_t*f){assert(style==2&&presents==1&&!memcmp(f,panel,FRAME_BYTES));}
static void epd_hl_set_all_white(EpdiyHighlevelState*h){(void)h;memset(pixels,255,FRAME_BYTES);}
static uint8_t*epd_hl_get_framebuffer(EpdiyHighlevelState*h){(void)h;return pixels;}
static void ui_lock_fallback_draw(uint8_t*f){memset(f,255,FRAME_BYTES);}
static bool display_system_binary_set(bool enabled){bool old=system_binary;system_binary=enabled;return old;}
static enum EpdDrawError update_display_full(EpdiyHighlevelState*h){(void)h;if(style==1)assert(!system_binary);++outputs;if(!output_ok)return EPD_DRAW_FAULT;memcpy(panel,pixels,FRAME_BYTES);++presents;return EPD_DRAW_SUCCESS;}
static enum EpdDrawError update_display_image_gray(EpdiyHighlevelState*h){assert(style==3&&draws[3]);uint8_t before=pixels[0];memset(panel,255,FRAME_BYTES);++image_clears;assert(pixels[0]==before);return update_display_full(h);}
static enum EpdDrawError update_display_white(EpdiyHighlevelState*h){(void)h;assert((style==0||style==2)&&lamp_off);++white_outputs;if(!white_ok)return EPD_DRAW_FAULT;memset(pixels,255,FRAME_BYTES);memset(panel,255,FRAME_BYTES);return EPD_DRAW_SUCCESS;}
static void guard_draw_result(EpdiyHighlevelState*h,enum EpdDrawError e){(void)h;assert(e==EPD_DRAW_SUCCESS||e==EPD_DRAW_FAULT);if(e==EPD_DRAW_FAULT)++white_faults;}
static void lock_hint_begin(EpdiyHighlevelState *h){(void)h;}
static void lock_hint_end(void){}
static void epd_poweroff(void){}
static void metalio_frontlight(unsigned b,unsigned w){assert(!b&&w==50);++lamp_off;}
static void metalio_frontlight_restore(void){++lamp_restore;}
static void read_pico_pmu_drain_events(void){}
static bool read_pico_transfer_pause_for_sleep(void){return transfer_ok;}
static void read_pico_transfer_resume_after_sleep(void){++resumes;}
static int ble_pt_suspend_for_sleep(void){return ble_ok?0:-1;}
static void ble_pt_resume_after_sleep(void){}
static void pico_boot_clear_resume(void){++cleared;}
static bool pico_boot_has_resume(void){return boot_cache;}
static bool pico_boot_lock_pending(void){return false;}
static bool metalio_boot_power_key(void){return false;}
static unsigned app_settings_wake_presses(void){return 1;}
static void read_pico_pmu_latch_power_wakeup(void){assert(false);}
static void app_settings_record_pin_lock(uint32_t at){assert(at==0||at>=1704067200);}
static void pico_boot_ready(void){}
static void pico_boot_hold_resume(void){}
static void app_font_begin_lock(app_lock_font_t*f){f->active=true;++begins;}
static void app_font_end_lock(app_lock_font_t*f){assert(f->active);++ends;}
static bool lock_screen_save(const uint8_t*f){assert(presents&&f==pixels&&!memcmp(panel,f,FRAME_BYTES));++saves;return cache_ok;}
static bool lock_screen_restore(uint8_t*f){if(!cache_ok||old_style!=style)return false;memset(f,0x10+style,FRAME_BYTES);return true;}
static void lock_wait_for_unlock(void*a){assert(a==(void*)1&&s_lock_sleep_touch==(void*)2);++waits;assert(!pin);}
static void lock_screen_authenticate(void*h,void*t,void*a,bool boot){(void)h;assert(t==(void*)2&&a==(void*)1&&pin&&boot==boot_cache);++auths;assert(pixels[0]==(decode_ok?0x10+style:0xff));}
static int64_t esp_timer_get_time(void){return 2000000;}
static int epd_width(void){return 1216;}
static int epd_height(void){return 684;}
static int read_pico_sd_get_info(read_pico_sd_info_t*i){i->mounted=true;return 0;}
static void vTaskDelay(int ms){assert(ms==20);}
'''
for name in ['lock_present_art','draw_wallpaper','enter_lock_and_sleep','app_lock_boot_gate']:u+=function(name,r/'main/sleep.c')+'\n'
u+=r'''
static void reset(void){media_resumes=0;memset(draws,0,sizeof(draws));presents=outputs=auths=begins=ends=resumes=cleared=waits=saves=lamp_off=lamp_restore=white_outputs=white_faults=image_clears=0;system_binary=pin=boot_cache=s_lock_feedback_started=s_lock_deep_ready=s_lock_frame_cached=false;s_lock_sleep_touch=NULL;decode_ok=transfer_ok=ble_ok=output_ok=white_ok=true;cache_ok=false;background=0x32;memset(panel,background,FRAME_BYTES);memset(pixels,0x99,FRAME_BYTES);}
int main(void){EpdiyHighlevelState hl={panel};
 for(int s=0;s<4;++s)for(int password=0;password<2;++password)for(int reader=0;reader<2;++reader){reset();style=s;pin=password;int64_t ignore=0;enter_lock_and_sleep(&hl,&ignore,(void*)1,(void*)2,reader);assert(white_outputs==(unsigned)(s==0||s==2)&&!white_faults);assert(draws[s]==1&&presents==1&&outputs==1&&auths==(unsigned)password&&waits==(unsigned)!password);assert(begins==(unsigned)(s==0||s==2||password)&&ends==begins&&resumes==1&&cleared==1&&lamp_off&&ignore==3000);assert(!s_lock_sleep_touch&&!s_lock_frame_cached&&saves==1&&media_resumes==1);}
 // Wallpaper keeps the old optical page throughout preparation, emits one complete image,
 // and restores inherited BW policy even on a failed first output / PIN failure path.
 for(int binary=0;binary<2;++binary)for(int password=0;password<2;++password)for(int failed=0;failed<2;++failed){reset();style=1;system_binary=binary;pin=password;output_ok=!failed;enter_lock_and_sleep(&hl,NULL,(void*)1,(void*)2,false);assert(system_binary==(bool)binary&&!white_outputs&&!image_clears);assert(outputs==(failed?2u:1u)&&presents==(unsigned)!failed&&saves==(unsigned)!failed);if(!failed)assert(panel[0]==0x11);}
 for(unsigned screen=0;screen<4;++screen){reset();style=3;background=0x21+screen*17;memset(panel,background,FRAME_BYTES);unsigned prior=image_clears;enter_lock_and_sleep(&hl,NULL,(void*)1,(void*)2,false);assert(!white_outputs&&draws[3]==1&&presents==1&&image_clears==prior+1);}
 for(int ready=0;ready<2;++ready)for(int password=0;password<2;++password)for(int cache=0;cache<2;++cache){reset();style=3;s_lock_deep_ready=ready;pin=password;cache_ok=cache;enter_lock_and_sleep(&hl,NULL,(void*)1,(void*)2,false);assert(saves==1&&!s_lock_frame_cached&&!s_lock_deep_ready);}
 for(int s=0;s<4;++s){reset();style=s;decode_ok=false;enter_lock_and_sleep(&hl,NULL,(void*)1,(void*)2,false);assert(draws[s]==1&&presents==1&&panel[0]==0xff&&style==s&&!saves);}
 for(int failed_style=0;failed_style<=3;++failed_style)for(int password=0;password<2;++password){reset();style=failed_style;pin=password;output_ok=false;unsigned prior=image_clears;enter_lock_and_sleep(&hl,NULL,(void*)1,(void*)2,false);assert(outputs==2&&!presents&&!saves);assert(image_clears==prior+(failed_style==3?2u:0u));if(password)assert(auths==1&&!lamp_restore);else assert(!waits&&!auths&&lamp_restore==1);}
 for(int password=0;password<2;++password){reset();style=2;pin=password;white_ok=false;enter_lock_and_sleep(&hl,NULL,(void*)1,(void*)2,false);assert(white_outputs==1&&white_faults==1&&outputs==1&&presents==1&&auths==(unsigned)password&&waits==(unsigned)!password);}
 reset();transfer_ok=false;enter_lock_and_sleep(&hl,NULL,(void*)1,(void*)2,false);assert(!outputs&&!begins&&!resumes&&cleared==1&&lamp_restore==1);
 reset();ble_ok=false;enter_lock_and_sleep(&hl,NULL,(void*)1,(void*)2,false);assert(!outputs&&!begins&&resumes==1&&cleared==1&&lamp_restore==1);
 for(int s=0;s<4;++s)for(int previous=0;previous<4;++previous){reset();style=s;old_style=previous;pin=boot_cache=cache_ok=true;app_lock_boot_gate(&hl,(void*)2,(void*)1);assert(auths==1&&begins==1&&ends==1&&outputs==(unsigned)(s!=previous)&&draws[s]==(unsigned)(s!=previous));}
 reset();app_lock_boot_gate(&hl,(void*)2,(void*)1);assert(!auths&&!begins);
 puts("PASS: S31 wallpaper presents once without white prepass and restores BW policy on failure; ticket/collage/transparent cleanup retained;PIN/failure/current-frame/success-only-cache/transfer/BLE/retained-wait boundaries");}
'''
with tempfile.TemporaryDirectory() as d:
 d=Path(d);(d/'test.c').write_text(u);subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-variable','-fsanitize=address,undefined',str(d/'test.c'),'-o',str(d/'test')],check=True);subprocess.run([str(d/'test')],check=True)
