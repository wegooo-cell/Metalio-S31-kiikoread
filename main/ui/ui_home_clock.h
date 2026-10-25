/* SPDX-License-Identifier: Apache-2.0
 * 中文：已确认首页时钟与同款时间页，静态表盘只读，绘制不分配内存。
 * English: Approved Home clocks and their matching time pages; read-only faces and allocation-free drawing.
 */
#pragma once
#include "ui_home_widget.h"
typedef enum {
    UI_HOME_CLOCK_PS1995, UI_HOME_CLOCK_ASTERISK,
    UI_HOME_CLOCK_MOON, UI_HOME_CLOCK_KEHAI, UI_HOME_CLOCK_DALI, UI_HOME_CLOCK_CAT, UI_HOME_CLOCK_HOUSE, UI_HOME_CLOCK_COUNT
} ui_home_clock_style_t;
// 两个有界槽容纳首页及放大时间页；只缓存字体无关底图，动态区域可裁剪复用。
// Two bounded slots fit Home and enlarged time faces; font-independent bases support cropped motion restores.
#define UI_HOME_CLOCK_BASE_SLOT_BYTES (504u*460u/2u)
#define UI_HOME_CLOCK_LIVE_CACHE_BYTES (2u*UI_HOME_CLOCK_BASE_SLOT_BYTES)
#if KIIKO_BOARD_METALIO47
// 两槽保留实时底图，另按样式保留固定预览，调用方统一分配PSRAM。
// Two live bases plus one fixed complete preview per style in the caller-owned PSRAM pool.
#define UI_HOME_CLOCK_BASE_CACHE_SLOTS (2u+UI_HOME_CLOCK_COUNT)
#define UI_HOME_CLOCK_PREVIEW_OFFSET (2u*UI_HOME_CLOCK_BASE_SLOT_BYTES)
#else
// Pico三槽LRU保留当前与邻近样式；空闲画布借用池前部，不再申请额外整屏。
// Pico keeps three LRU previews; idle rendering borrows the pool prefix without another full-frame allocation.
#define UI_HOME_CLOCK_BASE_CACHE_SLOTS 5u
#define UI_HOME_CLOCK_PREVIEW_OFFSET (1216u*684u/2u)
#endif
#define UI_HOME_CLOCK_BASE_CACHE_BYTES (UI_HOME_CLOCK_PREVIEW_OFFSET+(UI_HOME_CLOCK_BASE_CACHE_SLOTS-2u)*UI_HOME_CLOCK_BASE_SLOT_BYTES)
/// 在绘制外绑定缓冲；绘制过程不分配内存、不读文件。/ Bind outside drawing; rendering never allocates or reads files.
void ui_home_clock_bind_base_cache(uint8_t *memory,size_t bytes);
const char *ui_home_clock_name(ui_home_clock_style_t style);
void ui_home_clock_style_draw(uint8_t *fb,EpdRect bounds,const struct tm *date,bool binary,ui_home_clock_style_t style);
/// 固定10:10:30预览，完整保留字形和灰阶。/ Fixed10:10:30 preview retaining glyphs and grayscale.
void ui_home_clock_preview_draw(uint8_t *fb,EpdRect bounds,bool binary,ui_home_clock_style_t style);
void ui_home_clock_preview_invalidate(void);
/// 只查预览元数据，不绘制不分配。/ Metadata-only preview probe without drawing or allocation.
bool ui_home_clock_preview_cached(EpdRect bounds,bool binary,ui_home_clock_style_t style);
#if !KIIKO_BOARD_METALIO47
/// 空闲时借用池内画布预绘，不接触front/back或另占整屏；调用者保证无触摸/待推屏。
/// Borrow in-pool scratch while idle without touching front/back or allocating a frame; caller guards touch/pending output.
bool ui_home_clock_preview_prepare(EpdRect bounds,bool binary,ui_home_clock_style_t style);
#endif
/// 秒针旧/新位置的有界区域，用于恢复磨砂底色并局部移动圆点。/ Bounded old/new second positions for local frosted-background restoration.
EpdRect ui_home_clock_second_area(EpdRect bounds,const struct tm *before,const struct tm *after);
void ui_home_clock_style_draw_region(uint8_t *fb,EpdRect bounds,const struct tm *date,bool binary,ui_home_clock_style_t style,EpdRect clip);
/// 圆点每圈600小步，按实际时间取最新相位，跳过旧帧而不排队。
/// The dot uses 600 steps per circle; choose the current time phase and skip stale frames without queuing.
void ui_home_clock_phase_draw_region(uint8_t *fb,EpdRect bounds,const struct tm *date,bool binary,ui_home_clock_style_t style,EpdRect clip,unsigned phase);
EpdRect ui_home_clock_phase_area(EpdRect bounds,unsigned before,unsigned after);

/// 仅动态部件使用短局刷；静态表盘保持不变。/ Short partial updates move dynamic parts only.
bool ui_home_clock_has_motion(ui_home_clock_style_t style);
EpdRect ui_home_clock_motion_area(EpdRect bounds,unsigned before,unsigned after,ui_home_clock_style_t style);

/// 浅灰圆周轨迹最多一圈，保持经过的位置；仅活动圆点使用深灰。
/// Keep at most one lap of a light-gray circular trail, with a dark moving dot.
void ui_home_clock_trail_draw_region(uint8_t *fb,EpdRect bounds,const struct tm *date,bool binary,ui_home_clock_style_t style,EpdRect clip,unsigned phase,unsigned trail_start,unsigned trail_steps);
