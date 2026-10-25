/* SPDX-FileCopyrightText: 2026 mindreset
 * SPDX-License-Identifier: Apache-2.0
 * 中文：长按电源的滑动关机层；参考MokuReader液态玻璃，控件底图只在打开时存入PSRAM，关闭释放。
 * English: Slide-to-off layer with liquid glass inspired by MokuReader; snapshot controls in PSRAM on open and release on close.
 * 用户修订：滑动和点按只恢复控件底图并绘制局部反馈，不重新模糊、排字、写设置或调用硬件。
 * User revision: movement/presses restore cached controls without reblurring, shaping text, settings writes or hardware calls.
 */
#include "ui_power_dialog.h"
#include <stdlib.h>
#include <string.h>
#include "ui_kit.h"
#include "ui_glass.h"
#include "esp_heap_caps.h"

enum { HIT_NONE, HIT_SLIDER, HIT_RESTART, HIT_CANCEL };

static bool in_circle(int x, int y, int cx, int cy, int r) {
    int dx = x - cx, dy = y - cy;
    return abs(dx) <= r && abs(dy) <= r && dx * dx + dy * dy <= r * r;
}

static EpdRect slider_change(int before, int after) {
    if (before == after) return (EpdRect){0};
    int left = before < after ? before : after;
    return (EpdRect){UI_POWER_THUMB_X + left - UI_POWER_THUMB_R - 1,
        UI_POWER_THUMB_Y - UI_POWER_THUMB_R - 1,
        abs(after - before) + 2 * UI_POWER_THUMB_R + 3, 2 * UI_POWER_THUMB_R + 3};
}

static EpdRect button_area(int hit) {
    int x = hit == HIT_RESTART ? UI_POWER_RESTART_X : UI_POWER_CANCEL_X;
    return (EpdRect){x - UI_POWER_BUTTON_R - 1, UI_POWER_BUTTON_Y - UI_POWER_BUTTON_R - 1,
        2 * UI_POWER_BUTTON_R + 3, 2 * UI_POWER_BUTTON_R + 3};
}

void ui_power_dialog_reset(ui_power_dialog_t *dialog, bool touching) {
    if (!dialog) return;
    memset(dialog, 0, sizeof(*dialog));
    dialog->swallow = touching;
}

void ui_power_dialog_cancel_input(ui_power_dialog_t *dialog, EpdRect *dirty) {
    if (dirty) *dirty = (EpdRect){0};
    if (!dialog) return;
    if (dirty) {
        if (dialog->position) *dirty = slider_change(dialog->position, 0);
        else if (dialog->pressed) *dirty = button_area(dialog->hit);
    }
    ui_power_dialog_reset(dialog, true);
}

ui_power_action_t ui_power_dialog_feed(ui_power_dialog_t *dialog, const app_ctx_t *ctx, EpdRect *dirty) {
    if (!dirty) return UI_POWER_ACTION_NONE;
    *dirty = (EpdRect){0};
    if (!dialog) return UI_POWER_ACTION_NONE;
    if (!ctx || ctx->consumed || !ctx->touch ||
        (ctx->touch->touched && (ctx->touch->count != 1 ||
          ctx->touch->x >= UI_LOCK_WIDTH || ctx->touch->y >= UI_LOCK_HEIGHT))) {
        ui_power_dialog_cancel_input(dialog, dirty);
        return UI_POWER_ACTION_NONE;
    }
    const cst836u_touch_t *touch = ctx->touch;
    if (dialog->swallow) {
        if (!touch->touched) dialog->swallow = false;
        return UI_POWER_ACTION_NONE;
    }
    int x = touch->x, y = touch->y;
    if (ctx->pressed && touch->touched && !dialog->tracking) {
        dialog->tracking = true;
        dialog->x0 = x; dialog->y0 = y;
        dialog->started_ms = ctx->now_ms;
        int cx = UI_POWER_THUMB_X + dialog->position;
        if (in_circle(x, y, cx, UI_POWER_THUMB_Y, UI_POWER_THUMB_R + 6)) {
            dialog->hit = HIT_SLIDER;
            dialog->grab_x = x - cx;
        } else if (in_circle(x, y, UI_POWER_RESTART_X, UI_POWER_BUTTON_Y, UI_POWER_BUTTON_R)) {
            dialog->hit = HIT_RESTART;
        } else if (in_circle(x, y, UI_POWER_CANCEL_X, UI_POWER_BUTTON_Y, UI_POWER_BUTTON_R)) {
            dialog->hit = HIT_CANCEL;
        }
        if (dialog->hit >= HIT_RESTART) {
            dialog->pressed = true;
            *dirty = button_area(dialog->hit);
        }
    }
    if (!dialog->tracking) return UI_POWER_ACTION_NONE;
    if (ctx->now_ms < dialog->started_ms || (!touch->touched && !ctx->released)) {
        ui_power_dialog_cancel_input(dialog, dirty);
        return UI_POWER_ACTION_NONE;
    }
    if (dialog->hit == HIT_SLIDER) {
        // 捕获后可水平越界；垂直滑出取消，不能在别处抬手触发关机。
        // Capture permits horizontal overshoot; leaving vertically cancels, preventing off-track release shutdown.
        if (abs(y - UI_POWER_THUMB_Y) > UI_POWER_TRACK_H) {
            ui_power_dialog_cancel_input(dialog, dirty);
            return UI_POWER_ACTION_NONE;
        }
        if (touch->touched) {
            int next = x - dialog->grab_x - UI_POWER_THUMB_X;
            if (next < 0) next = 0;
            if (next > UI_POWER_SLIDE_RANGE) next = UI_POWER_SLIDE_RANGE;
            *dirty = slider_change(dialog->position, next);
            dialog->position = next;
        } else if (ctx->released) {
            if (dialog->position >= UI_POWER_SLIDE_COMMIT) {
                ui_power_dialog_reset(dialog, false);
                return UI_POWER_ACTION_SHUTDOWN;
            }
            ui_power_dialog_cancel_input(dialog, dirty);
            dialog->swallow = false;
        }
    } else if (dialog->hit >= HIT_RESTART) {
        int cx = dialog->hit == HIT_RESTART ? UI_POWER_RESTART_X : UI_POWER_CANCEL_X;
        if (!in_circle(x, y, cx, UI_POWER_BUTTON_Y, UI_POWER_BUTTON_R) ||
            abs(x - dialog->x0) > UI_TOUCH_SLOP_PX || abs(y - dialog->y0) > UI_TOUCH_SLOP_PX) {
            ui_power_dialog_cancel_input(dialog, dirty);
            if (!touch->touched) dialog->swallow = false;
        } else if (ctx->released) {
            ui_power_action_t action = dialog->hit == HIT_RESTART ? UI_POWER_ACTION_RESTART : UI_POWER_ACTION_CANCEL;
            ui_power_dialog_reset(dialog, false);
            return action;
        }
    } else if (ctx->released) {
        ui_power_dialog_reset(dialog, false);
    }
    return UI_POWER_ACTION_NONE;
}

EpdRect ui_power_dialog_rect(void) { return (EpdRect){0, 0, UI_LOCK_WIDTH, UI_LOCK_HEIGHT}; }

// 只缓存三个组件的4bpp底图，图形包含固定文字；不保留整页，也不在输入时分配。
// Cache three 4bpp components including fixed labels, without a full page or input-time allocation.
static uint8_t *s_control_backdrop;
static EpdRect power_track_rect(void) {
    return (EpdRect){UI_POWER_TRACK_X,UI_POWER_TRACK_Y,UI_POWER_TRACK_W,UI_POWER_TRACK_H};
}
static EpdRect power_button_rect(int slot) {
    int cx=slot==1?UI_POWER_RESTART_X:UI_POWER_CANCEL_X;
    return (EpdRect){cx-UI_POWER_BUTTON_R,UI_POWER_BUTTON_Y-UI_POWER_BUTTON_R,
                     2*UI_POWER_BUTTON_R,2*UI_POWER_BUTTON_R};
}
static size_t control_bytes(EpdRect r) {return ((size_t)r.width*r.height+1)/2;}
static uint8_t *control_slot(int slot) {
    if(!s_control_backdrop)return NULL;
    return s_control_backdrop+(slot?control_bytes(power_track_rect())+(slot-1)*control_bytes(power_button_rect(1)):0);
}
static void control_save(uint8_t *fb,int slot,EpdRect r) {
    uint8_t *dst=control_slot(slot);if(!dst)return;
    for(int y=0;y<r.height;++y)for(int x=0;x<r.width;++x){
        size_t at=(size_t)y*r.width+x;
        uint8_t value=ui_read_pixel(fb,r.x+x,r.y+y);
        if(at&1)dst[at/2]|=(uint8_t)(value<<4);else dst[at/2]=value;
    }
}
static void control_restore(uint8_t *fb,int slot,EpdRect r,EpdRect dirty) {
    const uint8_t *src=control_slot(slot);if(!src)return;
    int left=r.x>dirty.x?r.x:dirty.x,top=r.y>dirty.y?r.y:dirty.y;
    int right=r.x+r.width<dirty.x+dirty.width?r.x+r.width:dirty.x+dirty.width;
    int bottom=r.y+r.height<dirty.y+dirty.height?r.y+r.height:dirty.y+dirty.height;
    for(int y=top;y<bottom;++y)for(int x=left;x<right;++x){
        size_t at=(size_t)(y-r.y)*r.width+x-r.x;
        epd_draw_pixel(x,y,(uint8_t)(((src[at/2]>>((at&1)*4))&15)<<4),fb);
    }
}
static bool control_overlap(EpdRect a,EpdRect b) {
    return a.x<b.x+b.width&&b.x<a.x+a.width&&a.y<b.y+b.height&&b.y<a.y+a.height;
}
static void power_control_base(uint8_t *fb,int slot,bool glass) {
    EpdRect r=slot?power_button_rect(slot):power_track_rect();
    int radius=slot?UI_POWER_BUTTON_R:UI_POWER_TRACK_H/2;
    if(!glass||!ui_glass_panel(fb,r,radius,25,160)){
        ui_fill_round_rect(fb,r,radius,slot?0xf0:0xd0);
        ui_draw_control_frame(fb,r,radius,0x70);
    }
    if(!slot){
        ui_text_box(fb,(EpdRect){r.x+80,r.y+45,r.width-160,60},40,"滑动关机",EPD_DRAW_ALIGN_CENTER,false);
        return;
    }
    int cx=r.x+r.width/2,cy=r.y+r.height/2;
    // 重启和取消都用图标库的描边字形，和锁、电源同一套线宽。/ Restart and cancel both use the icon set's stroke marks, matching the lock and power line weight.
    ui_draw_icon(fb,cx,cy-20,44,slot==1?UI_ICON_ROTATE_CW:UI_ICON_X,UI_GRAY_BLACK);
    ui_text_box(fb,(EpdRect){cx-66,cy+18,132,38},24,slot==1?"重启":"取消",EPD_DRAW_ALIGN_CENTER,false);
}
void ui_power_dialog_end(void) {
    heap_caps_free(s_control_backdrop);s_control_backdrop=NULL;
}
void ui_power_dialog_draw_controls(uint8_t *fb,const ui_power_dialog_t *dialog,EpdRect dirty) {
    if(!fb||!dialog)return;
    for(int slot=0;slot<3;++slot){
        EpdRect r=slot?power_button_rect(slot):power_track_rect();
        if(!control_overlap(r,dirty))continue;
        if(s_control_backdrop)control_restore(fb,slot,r,dirty);
        else power_control_base(fb,slot,false);
        if(!slot){
            int cx=UI_POWER_THUMB_X+dialog->position;
            epd_fill_circle(cx,UI_POWER_THUMB_Y,UI_POWER_THUMB_R,0xc8,fb);
            ui_draw_icon(fb,cx,UI_POWER_THUMB_Y,52,UI_ICON_POWER,UI_GRAY_BLACK);
        }else if(dialog->pressed&&dialog->hit==slot+1){
            // 内环不覆盖文字或图标，抬手从缓存恢复原灰阶，不出现方框。
            // The inner ring avoids labels/icons; release restores original gray pixels without a box.
            for(int rr=UI_POWER_BUTTON_R-8;rr>=UI_POWER_BUTTON_R-11;--rr)
                epd_draw_circle(r.x+r.width/2,r.y+r.height/2,rr,UI_GRAY_BLACK,fb);
        }
    }
}
void ui_power_dialog_draw(uint8_t *fb,const ui_power_dialog_t *dialog) {
    if(!fb||!dialog)return;
    ui_power_dialog_end();
    size_t bytes=control_bytes(power_track_rect())+2*control_bytes(power_button_rect(1));
    s_control_backdrop=heap_caps_malloc(bytes,MALLOC_CAP_SPIRAM|MALLOC_CAP_8BIT);
    for(int slot=0;slot<3;++slot){
        power_control_base(fb,slot,s_control_backdrop!=NULL);
        control_save(fb,slot,slot?power_button_rect(slot):power_track_rect());
    }
    ui_power_dialog_draw_controls(fb,dialog,ui_power_dialog_rect());
}

void ui_power_final_draw(uint8_t *fb, bool restarting) {
    ui_clear_page(fb);
    const int cx = UI_LOCK_WIDTH / 2;
    ui_draw_icon(fb, cx, 486, 72, restarting ? UI_ICON_ROTATE_CW : UI_ICON_POWER, UI_GRAY_BLACK);
    ui_text(fb, cx, 548, 48, restarting ? "正在重启" : "kiikoread 已关机", EPD_DRAW_ALIGN_CENTER, false);
    if (!restarting) ui_text(fb, cx, 624, 26, "长按电源键开机", EPD_DRAW_ALIGN_CENTER, false);
}
