"""真实翻页与全屏重排回归，确保不跨过未读文字。/ Actual turns/reflow must not skip unread text.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import subprocess
import tempfile
from home_cover_cache_host_test import function

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'main/apps/app_book.c'
unit = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include "book/book_file_path.h"
typedef struct {int x,y,width,height;} EpdRect;
typedef struct {int64_t now_ms;int leaf;} app_ctx_t;
typedef enum {APP_REDRAW_NONE,APP_REDRAW_AREA,APP_REDRAW_PAGE} app_redraw_t;
enum {READING,TOC,SHELF,READER_PANEL_NONE,READER_PANEL_TOOLS};
#define BOOK_TOC_ROWS 7
#define MODE_GL16 1
#define E0470_TURN_RTL 1
#define E0470_TURN_LTR -1
#define ESP_LOGI(...) ((void)0)
static char s_requested_open[288];
static bool s_requested_fullscreen=true,s_requested_open_home;
// Real reader_zoom_reset dependencies: keep its cleanup in the exercised turn path.
#define READER_IMAGE_ZOOM_MIN 1000
static bool s_zoom_active,s_image_pan_active,s_image_zoom_bw;
static int s_zoom_slot,s_image_zoom;
static size_t s_image_zoom_page,s_zoom_bits_bytes;
static uint32_t s_image_zoom_start_distance;
static uint8_t *s_zoom_bits;
static struct {bool pending;} s_reader_tap;
static const char *s_text="text";
static size_t s_text_len=900,s_block_count,s_chapter,s_page,s_jump_offset;
static void *s_blocks;
static int s_px=48,s_reader_panel=READER_PANEL_NONE,s_reader_slider=-1,s_view=READING;
#define s_toolbar (s_reader_panel!=READER_PANEL_NONE)
static bool s_reader_fullscreen,s_clear_confirm,s_reader_text_frame,s_reader_turn_pending;
static bool s_reader_image_frame,s_reader_image_exit_pending;
static bool s_water_turn_pending,s_reader_cleanup,draw_locked,load_failed;
static int s_water_turn_dir;
static unsigned s_stats_pending_turns,s_session_turns,s_turns,s_unsaved;
static int64_t s_last_turn_ms,s_stats_activity_ms;
static bool s_save_failed;
static int s_turn_direction;
static char s_message[128];
static unsigned layout_span=100,reflows,paints,saves,failed_reflows;
static uint8_t full_pages;
static const char *app_settings_book_background_path(void){return "";}
static void copy_text(char *to,size_t cap,const char *from){snprintf(to,cap,"%s",from);}
static void lock_draw(void){assert(!draw_locked);draw_locked=true;}
static void unlock_draw(void){assert(draw_locked);draw_locked=false;}
static void invalidate_prep(void){}
static void refresh_chapter_lead(void){}
static EpdRect body_rect(void){return(EpdRect){0,0,684,s_reader_fullscreen?150:100};}
static size_t book_layout_page_start_offset(size_t page){return page*layout_span;}
static size_t book_layout_page_for_offset(size_t off){return off/layout_span;}
static size_t book_layout_page_count(void){return (s_text_len+layout_span-1)/layout_span;}
static bool book_layout_build_blocks(const char *text,size_t len,const void *blocks,size_t count,EpdRect r,int px){
 (void)text;(void)len;(void)blocks;(void)count;(void)px;assert(draw_locked);++reflows;
 if(failed_reflows){--failed_reflows;return false;}layout_span=r.height;return true;
}
static void release_page_images(void){}
static void prepare_inline_image(void){}
static void save_progress(void){++saves;}
static void free_book(void){assert(!draw_locked);s_text=NULL;}
static size_t book_chapter_count(void){return 2;}
static bool load_chapter(app_ctx_t *ctx,size_t chapter,int off,bool last){(void)ctx;(void)off;if(load_failed)return false;s_chapter=chapter;s_page=last?book_layout_page_count()-1:0;return true;}
static void set_reader_view(int view){s_view=view;}
// 目录实现另有真实源测试；这里记录边界失败返回的当前位置。/ TOC has its own source tests; track the failed-turn anchor here.
static size_t current_toc_position(void){return s_chapter;}
static int book_toc_open(size_t current){assert(current==s_chapter);return (int)current;}
static void skip_hidden_image_pages(app_ctx_t *ctx,int dir){(void)ctx;(void)dir;}
static uint8_t app_settings_reader_full_pages(void){return full_pages;}
static int effect=1;
static int app_settings_reader_turn_effect(void){return effect;}
static int test_images;
static int book_layout_page_image_count(size_t page){(void)page;return test_images;}
static app_redraw_t paint_reading(app_ctx_t *ctx,int mode){(void)ctx;assert(mode==MODE_GL16);++paints;return APP_REDRAW_AREA;}
'''
unit += r"""
static int indent=2,adjustment,layout_indent=2,layout_adjustment;
static int app_settings_book_indent(void){return indent;}
static int app_settings_book_indent_adjust(void){return adjustment;}
static void app_settings_set_book_indent(uint8_t em){indent=em;}
static void app_settings_set_book_indent_adjust(int8_t px){adjustment=px;}
static void book_layout_set_first_line_indent(unsigned em){assert(draw_locked);layout_indent=em;}
static void book_layout_set_first_line_indent_adjust(int px){assert(draw_locked);layout_adjustment=px;}
"""
unit += function('apply_reader_indent', BOOK) + '\n'
for name in ('reader_zoom_reset', 'app_book_request_open', 'app_book_request_open_from_home', 'app_book_request_resume',
             'toggle_reader_fullscreen', 'reader_turn_chrome', 'turn_page'):
    unit += function(name, BOOK) + '\n'
unit += r'''
static void reset(bool full,bool tools,size_t page,size_t chapter){
 s_reader_image_frame=s_reader_image_exit_pending=false;
 s_text="text";s_view=READING;s_reader_fullscreen=full;layout_span=full?150:100;s_page=page;s_chapter=chapter;
 s_reader_panel=tools?READER_PANEL_TOOLS:READER_PANEL_NONE;s_reader_slider=2;
 reflows=paints=saves=s_stats_pending_turns=s_session_turns=s_turns=s_unsaved=0;
 failed_reflows=0;load_failed=false;full_pages=0;s_reader_text_frame=true;
 s_reader_turn_pending=s_water_turn_pending=s_reader_cleanup=false;s_jump_offset=0;
}
int main(void){
 app_ctx_t ctx={.now_ms=1000};
 reset(true,false,2,0);size_t anchor=book_layout_page_start_offset(s_page);
 assert(apply_reader_indent(&ctx,2,-7)==APP_REDRAW_PAGE&&adjustment==-7&&layout_adjustment==-7&&indent==2);
 assert(book_layout_page_start_offset(s_page)==anchor&&saves==1);
 assert(apply_reader_indent(&ctx,2,-7)==APP_REDRAW_NONE&&saves==1);
 failed_reflows=1;
 assert(apply_reader_indent(&ctx,3,12)==APP_REDRAW_NONE&&indent==2&&adjustment==-7&&layout_indent==2&&layout_adjustment==-7&&saves==1);
 assert(book_layout_page_start_offset(s_page)==anchor&&!draw_locked);
 assert(apply_reader_indent(&ctx,2,101)==APP_REDRAW_NONE&&saves==1);

 assert(app_book_request_open("/sdcard/book.epub")&&s_requested_fullscreen&&!s_requested_open_home);
 assert(app_book_request_resume("/sdcard/book.epub",false)&&!s_requested_fullscreen&&s_requested_open_home);
 assert(app_book_request_open_from_home("/sdcard/other.epub")&&s_requested_fullscreen);
 assert(!app_book_request_open(NULL)&&!app_book_request_open(""));
 for(int full=0;full<2;++full)for(int tools=0;tools<2;++tools)for(int dir=-1;dir<=1;dir+=2){
  reset(full,tools,2,0);size_t destination=book_layout_page_start_offset(s_page+dir);
  s_zoom_bits=malloc(32);assert(s_zoom_bits);s_zoom_bits_bytes=32;
  s_zoom_active=s_image_pan_active=s_image_zoom_bw=s_reader_tap.pending=true;
  s_zoom_slot=2;s_image_zoom=2000;s_image_zoom_page=2;s_image_zoom_start_distance=99;
  app_redraw_t r=turn_page(&ctx,dir);
  assert(!s_zoom_bits&&!s_zoom_bits_bytes&&!s_zoom_active&&!s_image_pan_active&&!s_image_zoom_bw&&!s_reader_tap.pending);
  assert(s_zoom_slot==-1&&s_image_zoom==READER_IMAGE_ZOOM_MIN&&s_image_zoom_page==SIZE_MAX&&!s_image_zoom_start_distance);
  assert(s_reader_fullscreen&&s_reader_panel==READER_PANEL_NONE&&s_reader_slider==-1);
  assert(s_stats_pending_turns==1&&s_session_turns==1&&paints==1);
  assert(book_layout_page_start_offset(s_page)<=destination&&destination<book_layout_page_start_offset(s_page)+layout_span);
  assert(reflows==(unsigned)!full);
  assert(r==((!full||tools)?APP_REDRAW_PAGE:APP_REDRAW_AREA));
  assert(s_water_turn_pending==!!(full&&!tools));
 }
 // 普通文字恢复正式版的翻页与周期清屏标志。/ Restore release text-turn and periodic-cleanup state.
 effect=0;
 for(int tools=0;tools<2;++tools)for(int full=0;full<2;++full)for(int prior=0;prior<2;++prior){
  reset(full,tools,2,0);s_reader_text_frame=prior;full_pages=5;s_turns=4;
  assert(turn_page(&ctx,1)!=APP_REDRAW_NONE&&!s_water_turn_pending&&s_reader_cleanup);
 }
 reset(true,false,2,0);test_images=1;assert(turn_page(&ctx,1)==APP_REDRAW_AREA);
 test_images=0;effect=1;
 // Mixed/image targets and leaving an image never run the text ripple waveform.
 reset(true,false,2,0);test_images=2;assert(turn_page(&ctx,1)==APP_REDRAW_AREA&&!s_water_turn_pending&&!s_reader_turn_pending);
 reset(true,false,2,0);test_images=0;s_reader_text_frame=false;
 assert(turn_page(&ctx,1)==APP_REDRAW_AREA&&!s_water_turn_pending&&!s_reader_turn_pending);
 test_images=0;
 // An image that was actually displayed keeps its exit-cleaning state only on an area turn.
 reset(true,false,2,0);s_reader_image_frame=true;
 assert(turn_page(&ctx,1)==APP_REDRAW_AREA&&s_reader_image_exit_pending);
 reset(true,false,2,0);s_reader_image_exit_pending=true;
 assert(turn_page(&ctx,1)==APP_REDRAW_AREA&&!s_reader_image_exit_pending);
 reset(true,true,2,0);s_reader_image_frame=true;
 assert(turn_page(&ctx,1)==APP_REDRAW_PAGE&&!s_reader_image_exit_pending);
 reset(false,true,0,0);assert(turn_page(&ctx,-1)==APP_REDRAW_PAGE);
 assert(s_reader_fullscreen&&!s_toolbar&&s_page==0&&!paints&&!s_stats_pending_turns);
 reset(false,true,8,1);assert(turn_page(&ctx,1)==APP_REDRAW_PAGE);
 assert(s_reader_fullscreen&&!s_toolbar&&s_page==5&&!s_stats_pending_turns);
 reset(true,true,5,1);assert(turn_page(&ctx,1)==APP_REDRAW_PAGE&&!s_toolbar&&!reflows);
 reset(false,true,8,0);assert(turn_page(&ctx,1)==APP_REDRAW_PAGE&&s_chapter==1&&s_page==0&&s_reader_fullscreen);
 reset(false,true,0,1);assert(turn_page(&ctx,-1)==APP_REDRAW_PAGE&&s_chapter==0&&s_page==5&&s_reader_fullscreen);
 reset(false,true,8,0);load_failed=true;assert(turn_page(&ctx,1)==APP_REDRAW_PAGE&&s_view==TOC&&!paints&&!s_stats_pending_turns);
 reset(false,true,2,0);failed_reflows=1;assert(turn_page(&ctx,1)==APP_REDRAW_PAGE);
 assert(s_text&&!s_reader_fullscreen&&!s_toolbar&&layout_span==100&&s_page==3&&reflows==2);
 reset(false,true,2,0);failed_reflows=2;assert(turn_page(&ctx,1)==APP_REDRAW_PAGE);
 assert(!s_text&&s_view==SHELF&&!paints&&!s_stats_pending_turns&&s_message[0]);
 puts("PASS: native full-screen entry and explicit sleep overrides; old-layout destination anchors; toolbar dismissal; chapter/boundary turns; failed reflow restores safely or returns to the shelf");
}
'''
with tempfile.TemporaryDirectory(dir=ROOT / 'build') as folder:
    c, exe = Path(folder) / 'test.c', Path(folder) / 'test'
    c.write_text(unit)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined','-I'+str(ROOT/'main'),
                    str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
