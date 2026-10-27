/* SPDX-License-Identifier: Apache-2.0
 * 中文：独立锁屏输入循环；触摸键、蓝牙、拿起或冷启动不得绕过密码；已选宽限期仅在锁屏按键唤醒后判定。
 * English: Isolated locked-input loop; touch keys, BLE, pickup and cold starts cannot bypass the PIN; opt-in grace is checked only after lock-key wake.
 * 用户修订：读取失败或确认未开启时直接返回；正常读取的已有密码必须摘要验证，模糊缓存与局部输入保持。
 * User revision: return for read failure or confirmed disabled state; require digest verification for readable enabled PINs, retaining cached frost and local input.
 */
#include "lock_screen.h"
#include "lock_pin.h"
#include "settings.h"
#include "ui_pinpad.h"
#include "ui_kit.h"
#include "ui_lock_feedback.h"
#include "sleep.h"
#include "boot_state.h"
#include "display.h"
#include "e0470_epaper_waveform.h"
#include "read_pico_pmu.h"
#include "ble_page_turner.h"
#include "esp_timer.h"
#include "esp_heap_caps.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#define FRAME_BYTES (684u*1216u/2u)
#ifndef LOCK_SCREEN_CACHE_PARENT
#define LOCK_SCREEN_CACHE_PARENT "/sdcard/.readpico"
#endif
#define LOCK_ART_PATH LOCK_SCREEN_CACHE_PARENT "/locks/pin-background.bin"
// 旧缓存可能保存了临时圆锁；新代号仅持久化成功显示的真实锁图。
// Old caches may contain temporary badges; this generation persists only successfully displayed lock artwork.
#define ART_MAGIC UINT32_C(0x50414434)
typedef struct {uint32_t magic,rotation,style,checksum;uint64_t wallpaper;} art_header_t;
static uint32_t checksum(const uint8_t *bytes){uint32_t h=2166136261u;for(unsigned i=0;i<FRAME_BYTES;++i)h=(h^bytes[i])*16777619u;return h;}
static uint64_t wallpaper_key(void){
    if(app_settings_lock_style()!=1 && app_settings_lock_style()!=3)return 0;
    const char *path=app_settings_lock_style()==3?app_settings_bookmark_path():app_settings_wallpaper_path();
    uint64_t key=UINT64_C(14695981039346656037);
    for(const unsigned char *p=(const unsigned char*)path;*p;++p)key=(key^*p)*UINT64_C(1099511628211);
    struct stat st;
    if(stat(path,&st)==0){
        uint64_t info[2]={(uint64_t)st.st_size,(uint64_t)st.st_mtime};
        const unsigned char *bytes=(const unsigned char*)info;
        for(unsigned i=0;i<sizeof(info);++i)key=(key^bytes[i])*UINT64_C(1099511628211);
    }
    return key;
}
bool lock_screen_restore(uint8_t *frame){
    if(!frame)return false;
    FILE *f=fopen(LOCK_ART_PATH,"rb");if(!f)return false;art_header_t h;
    // 跨样式/换壁纸后先拒绝旧图，再由锁屏入口绘制当前选择；不多分配一帧。
    // Reject old art before reading pixels after a style/wallpaper change; the lock entry draws the current choice without another frame.
    bool ok=fread(&h,1,sizeof(h),f)==sizeof(h)&&h.magic==ART_MAGIC&&h.rotation==(uint32_t)epd_get_rotation()&&
        h.style==app_settings_lock_style()&&h.wallpaper==wallpaper_key()&&
        fread(frame,1,FRAME_BYTES,f)==FRAME_BYTES&&fgetc(f)==EOF&&h.checksum==checksum(frame);
    fclose(f);return ok;
}
bool lock_screen_save(const uint8_t *frame){
    (void)mkdir(LOCK_SCREEN_CACHE_PARENT,0775);(void)mkdir(LOCK_SCREEN_CACHE_PARENT "/locks",0775);
    FILE *f=fopen(LOCK_ART_PATH ".tmp","wb");if(!f)return false;
    art_header_t h={.magic=ART_MAGIC,.rotation=(uint32_t)epd_get_rotation(),
        .style=app_settings_lock_style(),.checksum=checksum(frame),.wallpaper=wallpaper_key()};
    bool ok=fwrite(&h,1,sizeof(h),f)==sizeof(h)&&fwrite(frame,1,FRAME_BYTES,f)==FRAME_BYTES&&fflush(f)==0;
    if(fclose(f))ok=false;
    if(ok) {
        // FatFS不支持覆盖rename；旧图保留为备份，失败时回滚，不把失败保存标记为可恢复。
        // FatFS cannot replace through rename; keep old art in a backup and roll back failures without marking them cached.
        if(rename(LOCK_ART_PATH ".tmp",LOCK_ART_PATH)==0)return true;
        (void)remove(LOCK_ART_PATH ".bak");
        if(rename(LOCK_ART_PATH,LOCK_ART_PATH ".bak")==0) {
            if(rename(LOCK_ART_PATH ".tmp",LOCK_ART_PATH)==0){(void)remove(LOCK_ART_PATH ".bak");return true;}
            (void)rename(LOCK_ART_PATH ".bak",LOCK_ART_PATH);
        }
    }
    (void)remove(LOCK_ART_PATH ".tmp");return false;
}
static void restore_art(uint8_t *fb,const uint8_t *original){
    if(original)memcpy(fb,original,FRAME_BYTES);
    else if(!lock_screen_restore(fb))ui_lock_fallback_draw(fb);
}
static void present(EpdiyHighlevelState *hl,EpdRect area){
    epd_poweron();enum EpdDrawError result=update_display_area_diff_with(hl,&E0470_WAVEFORM,MODE_GL16,area);
    guard_draw_result(hl,result);
    // 灰阶差分失败只重建同一密码画面，绝不进入未验证的页面。
    // On a display failure rebuild this same protected screen, never an unauthenticated page.
    if(result!=EPD_DRAW_SUCCESS)guard_draw_result(hl,update_display_full(hl));
}
static void present_input(EpdiyHighlevelState *hl,EpdRect area){
    enum EpdDrawError result=update_display_area_diff_with(hl,&E0470_FOLLOW_WAVEFORM,MODE_DU,area);
    guard_draw_result(hl,result);
    if(result!=EPD_DRAW_SUCCESS)present(hl,ui_pinpad_full());
}

void lock_screen_authenticate(EpdiyHighlevelState *hl,cst836u_handle_t touch,sc7a20h_handle_t acc,bool boot){
    if(!lock_pin_enabled())return;
    // 冷启动不免密；只有锁屏唤醒或有效深睡检查点允许使用已选宽限期。
    // Cold starts require the PIN; only lock wakes and valid deep resumes allow grace.
    const bool allow_grace = !boot || pico_boot_has_resume();
    uint8_t *fb=epd_hl_get_framebuffer(hl);
    (void)acc;
    (void)ble_pt_stop(2000);
    // Pico由锁屏入口保存确认成功的样式；启动/PIN不得覆盖它。
    // Pico persists validated art at the lock entry; boot/PIN must not overwrite it.
    uint8_t *original=heap_caps_get_free_size(MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT)>FRAME_BYTES+1024u*1024u
        ?heap_caps_malloc(FRAME_BYTES,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT):NULL;
    if(original)memcpy(original,fb,FRAME_BYTES);
    // 密码提示用纯白底：锁屏画面不再垫在密码控件下面，票根与数字互相透出且难读。
    // 等待阶段仍显示原锁屏样式；弹出提示时才整屏刷白画键盘，取消由 restore_art 恢复。
    // 键盘的玻璃圆键在 begin 时采样白底。
    // The PIN prompt takes a solid white base instead of layering the lock art beneath the
    // controls. The waiting phase keeps the original lock face; the prompt whitens the panel
    // before painting the pad, and cancel restores the face via restore_art. The pad's glass
    // keys sample the white ground at begin time.
    ui_fill_rect_fast((EpdRect){0,0,UI_LOCK_WIDTH,UI_LOCK_HEIGHT},UI_GRAY_WHITE,fb);
    ui_pinpad_t pad={0};ui_pinpad_begin(&pad,fb,"输入密码");
    restore_art(fb,original);
    bool waiting=true;
    unsigned failures=0;int64_t retry_at=0;
    for(;;){
        if(waiting){
            restore_art(fb,original);present(hl,ui_pinpad_full());
            if(!boot)app_lock_wait_key_idle(800);
            epd_poweroff();
            if(app_light_sleep_wait_timed(NULL,10u*60u*1000u)==APP_WAKE_TIMEOUT){
                ui_pinpad_end(&pad);free(original);app_enter_host_sleep(APP_SLEEP_DEEP);
                // 防御性处理：电源交接意外返回也继续验证。/ Defensive: a returning power handoff still requires verification.
                // 深睡回来 fb 是锁屏画面：先刷白让玻璃圆键重新采样，再由等待阶段恢复样式。
                // After deep sleep fb holds the lock art: white it so the glass keys resample,
                // then the waiting phase restores the art again.
                original=NULL;ui_fill_rect_fast((EpdRect){0,0,UI_LOCK_WIDTH,UI_LOCK_HEIGHT},UI_GRAY_WHITE,fb);
                ui_pinpad_begin(&pad,fb,"输入密码");
                continue;
            }
        }
        // 等待可能跨过宽限截止点；浅睡与深睡都在有效电源键唤醒后重新检查。
        // Waiting may cross the deadline; recheck after the validated power wake in both paths.
        if(allow_grace && lock_pin_grace_active()) {
            ui_pinpad_end(&pad);free(original);read_pico_pmu_drain_events();
            ble_pt_event_t e;while(ble_pt_pop_key(&e)){}
            ble_pt_raw_t raw;while(ble_pt_pop_raw(&raw)){}
            return;
        }
        app_lock_wait_key_idle(800);
        ui_pinpad_reset(&pad,"输入密码","");
        if(esp_timer_get_time()/1000<retry_at){pad.blocked=true;snprintf(pad.notice,sizeof(pad.notice),"请等待 10 秒后重试");}
        // 直接推送完整密码画面一次，不再补刷第二段背景。/ Present the complete PIN screen once, without a second backdrop stage.
        // 弹出提示才刷白：等待阶段 fb 是锁屏画面，这里整屏置白再画键盘；取消由 restore_art 恢复。
        // White only when the prompt appears: fb holds the lock art during waiting, so blank
        // the panel here before painting the pad; cancel restores the art via restore_art.
        ui_fill_rect_fast((EpdRect){0,0,UI_LOCK_WIDTH,UI_LOCK_HEIGHT},UI_GRAY_WHITE,fb);
        ui_pinpad_paint(fb,&pad,ui_pinpad_full());present(hl,ui_pinpad_full());
        // 密码等待不是启动失败；待验证时保留一次性恢复，不提前开书。
        // Waiting for a PIN is not a failed boot; hold one-shot resume without opening the book.
        if(boot){pico_boot_ready();pico_boot_hold_resume();boot=false;}
        ui_gesture_t gesture={0};bool was_down=false,draining=true;
        cst836u_touch_t latest={0};int64_t active_at=esp_timer_get_time()/1000,last_poll=active_at;
        bool cancel=false;
        while(!cancel){
            int64_t now=esp_timer_get_time()/1000;
            if(now-active_at>=30000){cancel=true;break;}
            if(now-last_poll>=40){last_poll=now;(void)read_pico_pmu_poll();if(read_pico_pmu_take_key_action()!=READ_PICO_PMU_KEY_NONE){cancel=true;break;}}
            if(pad.blocked&&lock_pin_available()&&now>=retry_at){ui_pinpad_reset(&pad,NULL,"请重新输入");ui_pinpad_paint(fb,&pad,ui_pinpad_entry_area());present(hl,ui_pinpad_entry_area());}
            cst836u_touch_t sample={0};esp_err_t error=cst836u_read(touch,&sample);
            bool down=error==ESP_OK&&sample.touched;
            if(draining){if(!down&&error==ESP_OK)draining=false;was_down=down;vTaskDelay(pdMS_TO_TICKS(5));continue;}
            if(down)latest=sample;else{latest.touched=false;latest.count=0;}
            app_ctx_t ctx={.now_ms=now,.touch=&latest,.pressed=down&&!was_down,.released=!down&&was_down,.consumed=error!=ESP_OK};
            ui_gesture_event_t event;
            if(ui_gesture_feed(&gesture,&ctx,&event)){
                active_at=now;EpdRect dirty;ui_pin_result_t r=ui_pinpad_handle(&pad,&event,&dirty);
                if(r==UI_PIN_CANCEL){cancel=true;break;}
                if(r!=UI_PIN_NONE){ui_pinpad_paint_input(fb,&pad);present_input(hl,dirty);}
                if(r==UI_PIN_COMPLETE){
                    bool verified=lock_pin_verify(pad.digits);
                    if(verified){ui_pinpad_end(&pad);free(original);read_pico_pmu_drain_events();ble_pt_event_t e;while(ble_pt_pop_key(&e)){}ble_pt_raw_t raw;while(ble_pt_pop_raw(&raw)){}return;}
                    ui_pinpad_reset(&pad,NULL,"密码不正确，请重试");
                    if(++failures>=3){failures=0;retry_at=now+10000;pad.blocked=true;snprintf(pad.notice,sizeof(pad.notice),"请等待 10 秒后重试");}
                    ui_pinpad_paint(fb,&pad,ui_pinpad_entry_area());present(hl,ui_pinpad_entry_area());
                }
            }
            was_down=down;vTaskDelay(pdMS_TO_TICKS(5));
        }
        ui_pinpad_reset(&pad,NULL,"");waiting=true;
    }
}
