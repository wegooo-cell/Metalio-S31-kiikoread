#!/usr/bin/env python3
"""中文：执行S31启动门禁，真实唤醒不多等一次，定时/共享IRQ不能自行解锁。
English: Execute S31 boot gates: retain real wakes without granting timer/shared-IRQ unlocks.
"""
from pathlib import Path
import subprocess, tempfile
from home_cover_cache_host_test import function
root=Path(__file__).resolve().parents[1]
source=root/'main/sleep.c'
unit=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define ESP_OK 0
#define ESP_ERR_NOT_FINISHED 1
#define ESP_RST_POWERON 1
#define ESP_RST_DEEPSLEEP 5
#define ESP_SLEEP_WAKEUP_EXT1 2
#define READ_PICO_IOE_INT_GPIO 2
#define APP_LOCK_IDLE_TIMEOUT_MS 0
#define EPD_DRAW_SUCCESS 0
#define pdMS_TO_TICKS(x) (x)
typedef int esp_err_t;
typedef int app_wake_source_t;
typedef void *sc7a20h_handle_t;
typedef void *cst836u_handle_t;
typedef struct{int marker;}EpdiyHighlevelState;
typedef struct{bool mounted;}read_pico_sd_info_t;
typedef struct{int marker;}app_lock_font_t;
enum EpdDrawError{EPD_OK};
enum{APP_WAKE_KEY,APP_WAKE_PICKUP,APP_WAKE_TIMEOUT};
static bool s_boot_from_deep,s_boot_power_wake,s_boot_power_on,s_boot_lock_draw;
static int reset_reason,cause,wake_presses;
static uint64_t ext1;
static bool resume,pin,physical,queued,prior_lock;
static unsigned waits,latches,auth,holds,ready,frames,hints,manual_presses,clears;
static int esp_reset_reason(void){return reset_reason;}
static int esp_sleep_get_wakeup_cause(void){return cause;}
static uint64_t esp_sleep_get_ext1_wakeup_status(void){return ext1;}
static bool metalio_boot_power_key(void){return physical;}
static bool lock_pin_enabled(void){return pin;}
static int app_settings_wake_presses(void){return wake_presses;}
static bool pico_boot_has_resume(void){return resume;}
static bool pico_boot_lock_pending(void){return prior_lock;}
static void pico_boot_clear_resume(void){assert(prior_lock&&!resume);prior_lock=false;++clears;}
static void pico_boot_ready(void){++ready;}
static void pico_boot_hold_resume(void){++holds;}
static void lock_hint_begin(EpdiyHighlevelState *h){assert(h);++hints;}
static void lock_hint_end(void){assert(hints);--hints;}
static void lock_resume_service(void){}
static bool app_lock_resume_frame(EpdiyHighlevelState *h){assert(!h);++frames;return false;}
static void read_pico_pmu_latch_power_wakeup(void){assert(physical);queued=true;++latches;}
static int app_light_sleep_wait_timed(void *acc,unsigned ms){
 assert(!acc&&!ms);++waits;
 if(queued){queued=false;return APP_WAKE_KEY;}
 // The mock returns only after a later real user press; record when it was required.
 ++manual_presses;return APP_WAKE_KEY;
}
static int read_pico_sd_get_info(read_pico_sd_info_t *i){i->mounted=true;return ESP_OK;}
static void vTaskDelay(unsigned ms){(void)ms;}
static void app_font_begin_lock(app_lock_font_t *f){f->marker=1;}
static void app_font_end_lock(app_lock_font_t *f){assert(f->marker);}
static uint8_t fb[32];
static uint8_t *epd_hl_get_framebuffer(EpdiyHighlevelState *h){assert(h);return fb;}
static bool lock_screen_restore(uint8_t *f){assert(f==fb);return true;}
static int app_settings_lock_style(void){return 0;}
static int epd_width(void){return 8;}static int epd_height(void){return 8;}
static bool book_ticket_draw(uint8_t *f,bool b){assert(f==fb&&!b);return true;}
static bool book_lock_collage_prepare(uint8_t *f){assert(f==fb);return true;}
static const char *app_settings_bookmark_path(void){return "";}
static bool book_lock_bookmark_draw(uint8_t *f,const char *p){(void)p;assert(f==fb);return true;}
static bool draw_wallpaper(uint8_t *f){assert(f==fb);return true;}
static void ui_lock_fallback_draw(uint8_t *f){assert(f==fb);}
static enum EpdDrawError lock_present_art(EpdiyHighlevelState *h,int s){(void)s;assert(h);return EPD_OK;}
static void guard_draw_result(EpdiyHighlevelState *h,enum EpdDrawError e){assert(h&&!e);}
static void epd_poweroff(void){}
static bool lock_screen_save(uint8_t *f){assert(f==fb);return true;}
static void lock_screen_authenticate(EpdiyHighlevelState *h,void *t,void *a,bool b){assert(h&&t&&a&&b);++auth;}
'''
unit+='#include <string.h>\n'
for name in ('app_lock_capture_boot_wakeup','lock_wait_for_unlock','app_lock_boot_gate'):
    unit+=function(name,source)+'\n'
unit+=r'''
static void reset(void){
 s_boot_from_deep=s_boot_power_wake=s_boot_power_on=s_boot_lock_draw=false;
 reset_reason=ESP_RST_POWERON;cause=0;ext1=0;wake_presses=1;
 resume=true;pin=physical=queued=prior_lock=false;
 waits=latches=auth=holds=ready=frames=hints=manual_presses=clears=0;
}
static void gate(void){EpdiyHighlevelState hl={0};app_lock_capture_boot_wakeup();app_lock_boot_gate(&hl,(void*)1,(void*)2);assert(!hints&&frames==1);}
int main(void){
 reset();physical=true;gate();assert(!waits&&!manual_presses&&ready==1&&holds==1);
 reset();reset_reason=ESP_RST_DEEPSLEEP;cause=ESP_SLEEP_WAKEUP_EXT1;ext1=4;physical=true;
 gate();assert(waits==1&&latches==1&&!manual_presses);
 reset();gate();assert(waits==1&&manual_presses==1&&!latches);
 // Missing physical evidence, timer wake, another GPIO and software reset retain the lock.
 for(unsigned i=0;i<4;i++){
  reset();reset_reason=ESP_RST_DEEPSLEEP;cause=ESP_SLEEP_WAKEUP_EXT1;ext1=4;physical=true;
  if(i==0)physical=false;else if(i==1)cause=4;else if(i==2)ext1=8;else reset_reason=3;
  gate();assert(waits==1&&!latches&&manual_presses==1);
 }
 reset();wake_presses=2;gate();assert(waits==1&&!latches&&manual_presses==1);
 reset();wake_presses=2;reset_reason=ESP_RST_DEEPSLEEP;cause=ESP_SLEEP_WAKEUP_EXT1;ext1=4;physical=true;
 gate();assert(waits==1&&!latches&&manual_presses==1);
 // PIN always reaches authentication, independent of boot cause or the single/double choice.
 for(unsigned i=0;i<3;i++){
  reset();pin=true;reset_reason=i==0?ESP_RST_POWERON:ESP_RST_DEEPSLEEP;
  cause=ESP_SLEEP_WAKEUP_EXT1;ext1=4;physical=true;gate();assert(auth==1&&!latches);
 }
 reset();resume=false;gate();assert(!waits&&!latches&&!holds);
 // Watchdog recovery may forbid book/font resume while still retaining the prior lock.
 reset();resume=false;prior_lock=true;reset_reason=7;gate();assert(waits==1&&!latches&&manual_presses==1&&clears==1&&!prior_lock);
 reset();resume=false;prior_lock=true;reset_reason=7;pin=true;gate();assert(auth==1&&clears==1&&!prior_lock);
 reset();prior_lock=true;gate();assert(waits==1&&!clears&&prior_lock);
 puts("PASS: S31 actual boot gate, single hardware boot, confirmed deep key, no shared-IRQ/timer/software-reset auto unlock, double/PIN retained");
}
'''
with tempfile.TemporaryDirectory(prefix='s31-boot-wake-') as d:
    p=Path(d);(p/'test.c').write_text(unit)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
