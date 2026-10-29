"""图片页实际生命周期及低内存回归。/ Actual image-page lifecycle and low-memory regression.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import re
import subprocess
import tempfile
from board_source_view import select_source
root = Path(__file__).resolve().parents[1]
raw_source = (root/'main/apps/app_image.c').read_text()
prefix = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/stat.h>
#include <unistd.h>
#include <dirent.h>
#define UI_LOCK_WIDTH 684
#define UI_LOCK_HEIGHT 1216
#define UI_GRAY_LIGHT 192
#define UI_GRAY_WHITE 255
#define EPD_DRAW_ALIGN_LEFT 0
#define EPD_DRAW_ALIGN_CENTER 1
#define EPD_DRAW_ALIGN_RIGHT 2
#define UI_KEY_2 2
#define MALLOC_CAP_SPIRAM 1
#define MALLOC_CAP_8BIT 2
typedef struct {int x,y,width,height;} EpdRect;
typedef enum {APP_REDRAW_NONE,APP_REDRAW_PAGE,APP_REDRAW_FULL} app_redraw_t;
typedef struct {uint8_t *fb;void *hl,*request_app;bool request_return;} app_ctx_t;
typedef enum {UI_GESTURE_SWIPE_L,UI_GESTURE_SWIPE_R,UI_GESTURE_TAP} gesture_type;
typedef struct {gesture_type type;int x0,y0;} ui_gesture_event_t;
typedef struct {const char *title,*detail;bool enter_full,owns_keys,binary_ui;bool(*menu_handle_enabled)(app_ctx_t*),(*edge_back_enabled)(app_ctx_t*);void(*on_enter)(app_ctx_t*),(*on_exit)(app_ctx_t*),(*on_media_lost)(app_ctx_t*),(*render)(app_ctx_t*,uint8_t*);bool(*present)(app_ctx_t*,app_redraw_t);app_redraw_t(*on_key)(app_ctx_t*,int),(*on_gesture)(app_ctx_t*,const ui_gesture_event_t*);} app_desc_t;
typedef struct {bool mounted;} read_pico_sd_info_t;
static int test_alloc_fail,test_malloc_fail,test_dimensions_fail,test_decode_fail,test_decodes,test_presentations;
static unsigned test_pixels,test_mono_calls,test_list_calls,test_hint_calls;
static bool test_tall;
#if 1
static char wallpaper[288],bookmark[288];static unsigned lock_style_returns;
static void app_device_settings_resume_lock_style(void){++lock_style_returns;}static unsigned lock_style,setting_writes;
static const char *app_settings_wallpaper_path(void){return wallpaper;}
static const char *app_settings_bookmark_path(void){return bookmark;}
static unsigned app_settings_lock_style(void){return lock_style;}
static void app_settings_set_wallpaper_path(const char *p){snprintf(wallpaper,sizeof(wallpaper),"%s",p);++setting_writes;}
static void app_settings_set_bookmark_path(const char *p){snprintf(bookmark,sizeof(bookmark),"%s",p);++setting_writes;}
static void app_settings_set_lock_style(unsigned s){lock_style=s;++setting_writes;}
#endif
static bool test_mounted;
enum EpdDrawError {EPD_DRAW_SUCCESS};
#define MODE_DU 1
#define MODE_GL16 5
#if KIIKO_BOARD_METALIO47
static const int E0470_FULL_WAVEFORM=0;
static bool test_binary;
static void display_main_transition_cancel(void){}
static enum EpdDrawError update_display_area_full_with(void *hl,const int *wave,int mode,EpdRect area){(void)hl;assert(!test_binary&&wave==&E0470_FULL_WAVEFORM&&mode==MODE_GL16&&area.x==0&&area.y==0&&area.width==684&&area.height==1216);++test_presentations;return 0;}
typedef enum {UI_ICON_LOCK,UI_ICON_HOUSE,UI_ICON_BOOKMARK,UI_ICON_CHEVRON_RIGHT} ui_icon_t;
static bool glass_fail;
static bool ui_glass_panel_frost(uint8_t *fb,EpdRect r,int radius,int white,int refract,bool soften){(void)fb;assert(r.x==70&&r.y==346&&r.width==544&&(r.height==468||r.height==372)&&radius==28&&white>=95&&refract==3&&soften);return !glass_fail;}
static void ui_draw_icon(uint8_t *fb,int x,int y,int size,ui_icon_t icon,uint8_t gray){(void)fb;(void)x;(void)y;(void)size;(void)icon;assert(!gray);}
static void ui_draw_button(uint8_t *fb,EpdRect r,const char *text,bool on){(void)fb;assert((r.y==642||r.y==546)&&!strcmp(text,"取消")&&!on);}

static bool display_system_binary_set(bool binary){bool previous=test_binary;test_binary=binary;return previous;}
static void display_monochrome_frame(uint8_t *fb){++test_mono_calls;for(size_t i=0;i<684u*1216u;++i)fb[i]=fb[i]<128?0:255;}
static enum EpdDrawError update_display_mode_diff(void *hl,int mode){(void)hl;assert(test_binary&&mode==MODE_DU);++test_list_calls;return EPD_DRAW_SUCCESS;}
static enum EpdDrawError update_display_full(void *hl){(void)hl;if(test_binary)++test_list_calls;else ++test_presentations;return EPD_DRAW_SUCCESS;}
#endif
#if !KIIKO_BOARD_METALIO47
static const int E0470_FULL_WAVEFORM=0;
static bool test_binary;
typedef enum {UI_ICON_LOCK,UI_ICON_HOUSE,UI_ICON_BOOKMARK,UI_ICON_CHEVRON_RIGHT} ui_icon_t;
static bool glass_fail;
static bool ui_glass_panel_frost(uint8_t *fb,EpdRect r,int radius,int white,int refract,bool soften){(void)fb;assert(r.x==70&&r.y==346&&r.width==544&&(r.height==468||r.height==372)&&radius==28&&white>=95&&refract==3&&soften);return !glass_fail;}
static void ui_draw_icon(uint8_t *fb,int x,int y,int size,ui_icon_t icon,uint8_t gray){(void)fb;(void)x;(void)y;(void)size;(void)icon;assert(!gray);}
static void ui_draw_button(uint8_t *fb,EpdRect r,const char *text,bool on){(void)fb;assert((r.y==642||r.y==546)&&!strcmp(text,"取消")&&!on);}

static enum EpdDrawError update_display_area_diff_with(void *hl,const int *wave,int mode,EpdRect area){(void)hl;assert(wave==&E0470_FULL_WAVEFORM&&mode==MODE_GL16&&area.x==0&&area.y==0&&area.width==684&&area.height==1216);++test_presentations;return 0;}
static enum EpdDrawError update_display_full(void *hl){(void)hl;++test_presentations;return EPD_DRAW_SUCCESS;}
#endif
static void *heap_caps_calloc(size_t n,size_t size,int cap){(void)cap;return test_alloc_fail?NULL:calloc(n,size);}
static void *heap_caps_malloc(size_t n,int cap){(void)cap;if(test_malloc_fail&&!--test_malloc_fail)return NULL;return malloc(n);}
static void read_pico_sd_get_info(read_pico_sd_info_t *out){out->mounted=test_mounted;}
static const uint8_t display_test_png_start[]={1,2,3,4},display_test_png_end[]={0};
static bool book_image_dimensions(const uint8_t *data,size_t size,bool png,unsigned *w,unsigned *h){(void)png;assert(data&&size>=4);if(test_dimensions_fail)return false;*w=300;*h=test_tall?2400:400;return true;}
static bool book_image_grayscale(const uint8_t *data,size_t size,bool png,unsigned w,unsigned h,uint8_t *out){(void)png;assert(data&&size>=4&&w<=684&&h<=1216);++test_decodes;if(test_decode_fail)return false;for(size_t i=0;i<(size_t)w*h;++i)out[i]=(i%16)*17;return true;}
static void ui_clear_page(uint8_t *fb){memset(fb,255,684u*1216u);}
uint8_t ui_image_dither_gray(uint8_t gray,int x,int y);
static void epd_draw_pixel(int x,int y,int gray,uint8_t *fb){assert(x>=0&&y>=0&&x<684&&y<1216);fb[(size_t)y*684+x]=(uint8_t)gray;++test_pixels;}
static void ui_nav_status(uint8_t *fb){(void)fb;}
static void ui_nav_back(uint8_t *fb,int x,int y){(void)fb;(void)x;(void)y;}
static void ui_nav_draw(uint8_t *fb,int tab){(void)fb;(void)tab;}
static void ui_text_vc(uint8_t *fb,int x,int y,int size,const char *text,int align,bool bold){(void)fb;(void)x;(void)size;(void)align;(void)bold;if(!strncmp(text,"左右滑动切换图片",24)){assert(y==1188);++test_hint_calls;}}
static void ui_text(uint8_t *fb,...){(void)fb;}
static void ui_hairline(uint8_t *fb,...){(void)fb;}
static void ui_fill_round_rect(uint8_t *fb,...){(void)fb;}
static void ui_draw_round_rect(uint8_t *fb,...){(void)fb;}
static enum EpdDrawError update_display_image_gray(void *hl){(void)hl;++test_presentations;return 0;}
static void guard_draw_result(void *hl,int result){(void)hl;assert(!result);}
static void *app_home_page(void){return NULL;}
static int ui_nav_hit(int x,int y){(void)x;(void)y;return -1;}
static void ui_nav_request(app_ctx_t *ctx,int tab){(void)ctx;(void)tab;}
static bool ui_rect_hit(EpdRect r,int x,int y){return x>=r.x&&y>=r.y&&x<r.x+r.width&&y<r.y+r.height;}
#define BOOK_IMAGE_FILE_MAX (50u*1024u*1024u)
static bool book_image_file_dimensions(const char *path,bool png,unsigned *w,unsigned *h){(void)path;return book_image_dimensions((const uint8_t*)"IMG!",4,png,w,h);}
static bool book_image_file_grayscale(const char *path,bool png,unsigned w,unsigned h,uint8_t *out){(void)path;return book_image_grayscale((const uint8_t*)"IMG!",4,png,w,h,out);}
"""
tail = r"""
static void image_fixture(const char *name){FILE *f=fopen(name,"wb");assert(f);assert(fwrite("IMG!",1,4,f)==4);assert(!fclose(f));}
int main(void){
 char root[]="/tmp/pico-images-XXXXXX",path[256],other[256];assert(mkdtemp(root));
 snprintf(path,sizeof(path),"%s/first.png",root);image_fixture(path);
 snprintf(other,sizeof(other),"%s/second.jpeg",root);image_fixture(other);
 static uint8_t fb[684u*1216u];app_ctx_t ctx={.fb=fb};
 // 首次进入时没有列表：故障注入不得解引用空指针。/ First-entry list allocation failure must never dereference NULL.
 test_alloc_fail=1;assert(app_image_request_open(path));on_enter(&ctx);assert(!s_count&&!s_viewing&&!s_items&&strstr(s_message,"内存不足"));render(&ctx,fb);
 test_alloc_fail=0;assert(app_image_request_open(path));on_enter(&ctx);assert(s_viewing&&s_count==2&&s_selected==0&&!strcmp(s_items[0].path,path));assert(test_decodes==1);
 unsigned before_mono=test_mono_calls;
 assert(present(&ctx,APP_REDRAW_PAGE)&&test_presentations==1&&test_pixels==(size_t)s_width*s_height);
 assert(test_mono_calls==before_mono);
 unsigned levels=0;for(size_t i=0;i<sizeof(fb);++i){assert(fb[i]%17==0);levels|=1u<<(fb[i]/17);}assert(levels==65535);
#if 1
 assert(test_hint_calls==1);
 assert(!app_image.binary_ui);
 uint8_t *decoded=s_gray;int selected=s_selected;
 ui_gesture_event_t tap={.type=UI_GESTURE_TAP,.x0=342,.y0=600};
 assert(on_gesture(&ctx,&tap)==APP_REDRAW_PAGE&&s_lock_menu&&s_viewing&&s_gray==decoded&&!image_edge_back(&ctx));
 unsigned hints=test_hint_calls;int presentations=test_presentations;
 for(unsigned fail=0;fail<2;++fail){glass_fail=fail;test_binary=true;assert(present(&ctx,APP_REDRAW_PAGE));assert(test_binary&&test_hint_calls==hints&&test_presentations==++presentations);}
 test_binary=false;glass_fail=false;
 ui_gesture_event_t swipe={.type=UI_GESTURE_SWIPE_L};
 assert(on_gesture(&ctx,&swipe)==APP_REDRAW_NONE&&s_selected==selected);
 tap.y0=682;assert(on_gesture(&ctx,&tap)==APP_REDRAW_PAGE&&!s_lock_menu&&!setting_writes&&s_gray==decoded);
 tap.y0=600;on_gesture(&ctx,&tap);tap.y0=484;
 assert(on_gesture(&ctx,&tap)==APP_REDRAW_PAGE&&!s_lock_menu&&lock_style==1&&!strcmp(wallpaper,path)&&s_gray==decoded);
 tap.y0=600;on_gesture(&ctx,&tap);tap.y0=586;
 assert(on_gesture(&ctx,&tap)==APP_REDRAW_PAGE&&!s_lock_menu&&lock_style==3&&!strcmp(bookmark,path));
 assert(move_image(1)==APP_REDRAW_PAGE&&s_viewing&&!s_items[s_selected].png);
 tap.y0=600;on_gesture(&ctx,&tap);tap.y0=586;unsigned writes=setting_writes;
 assert(on_gesture(&ctx,&tap)==APP_REDRAW_PAGE&&s_lock_menu&&setting_writes==writes&&lock_style==3);
 assert(on_key(&ctx,0)==APP_REDRAW_PAGE&&!s_lock_menu&&s_viewing);
 swipe.type=UI_GESTURE_SWIPE_R;assert(on_gesture(&ctx,&swipe)==APP_REDRAW_PAGE&&s_selected==0);
#else
 assert(app_image.binary_ui);
#endif
 assert(move_image(1)==IMAGE_ACTION_REDRAW&&s_viewing&&s_selected==1&&!strcmp(s_items[1].path,other));
 test_tall=true;assert(load_image(0));
#if KIIKO_BOARD_METALIO47
 assert(s_height==1160);
 for(unsigned policy=0;policy<2;++policy){test_binary=policy;assert(present(&ctx,APP_REDRAW_PAGE));assert(test_binary==policy);}
#else
 assert(s_height==1160);
#endif
 test_tall=false;
 image_on_exit(&ctx);assert(!s_gray&&!s_viewing);
#if KIIKO_BOARD_METALIO47
 for(unsigned policy=0;policy<2;++policy){test_binary=policy;assert(present(&ctx,APP_REDRAW_PAGE));assert(test_binary==policy);assert(present(&ctx,APP_REDRAW_FULL));assert(test_binary==policy);}
 assert(test_list_calls==4&&test_mono_calls==before_mono+4);
#else
 assert(!present(&ctx,APP_REDRAW_PAGE)&&test_list_calls==0);
#endif
 // 名单达到上限时，文件管理选择的文件仍必须能直接打开。/ Directly selected Files images must open even after the list limit.
 char fixture[256];for(int i=0;i<100;++i){snprintf(fixture,sizeof(fixture),"%s/image%03d.jpg",root,i);image_fixture(fixture);}
 assert(app_image_request_open(other));on_enter(&ctx);assert(s_count==IMAGE_MAX&&s_viewing&&s_selected==0&&!strcmp(s_items[0].path,other));image_on_exit(&ctx);
 for(int fail=1;fail<=1;++fail){test_malloc_fail=fail;assert(app_image_request_open(path));on_enter(&ctx);assert(!s_gray&&!s_viewing&&s_message[0]);}
 test_dimensions_fail=1;assert(app_image_request_open(path));on_enter(&ctx);assert(!s_gray&&!s_viewing);test_dimensions_fail=0;
 test_decode_fail=1;assert(app_image_request_open(path));on_enter(&ctx);assert(!s_gray&&!s_viewing);test_decode_fail=0;
 assert(app_image_request_open(path));on_enter(&ctx);assert(s_viewing);on_media_lost(&ctx);assert(!s_gray&&!s_viewing);
#if KIIKO_BOARD_METALIO47
 // 两个受限入口用同一16灰呈现器，取消/退出/重新从文件管理打开不得串模式。
 // Both scoped entries share the16-tone presenter; cancellation/exit/later Files opens cannot leak modes.
 for(int transparent=0;transparent<2;++transparent){
  assert(app_image_request_lock_picker(path,transparent));on_enter(&ctx);
  assert(s_viewing&&!image_edge_back(&ctx)&&image_lock_action_count()==1&&s_lock_mode==(transparent?IMAGE_LOCK_BOOKMARK:IMAGE_LOCK_WALLPAPER));
  if(transparent)for(int i=0;i<s_count;++i)assert(s_items[i].png);
  unsigned writes=setting_writes;tap.y0=600;assert(on_gesture(&ctx,&tap)==APP_REDRAW_PAGE&&s_lock_menu);
  for(int policy=0;policy<2;++policy){test_binary=policy;assert(present(&ctx,APP_REDRAW_PAGE));assert(test_binary==policy);}
  tap.y0=586;assert(on_gesture(&ctx,&tap)==APP_REDRAW_PAGE&&!s_lock_menu&&setting_writes==writes);
  tap.y0=600;on_gesture(&ctx,&tap);tap.y0=484;
  assert(on_gesture(&ctx,&tap)==APP_REDRAW_PAGE&&!s_lock_menu&&lock_style==(transparent?3:1)&&setting_writes==writes+2);
  assert(on_key(&ctx,0)==APP_REDRAW_PAGE&&!s_viewing&&image_edge_back(&ctx));
  unsigned returns=lock_style_returns;ctx.request_return=false;
  assert(on_key(&ctx,0)==APP_REDRAW_NONE&&ctx.request_return&&lock_style_returns==returns+1);
  image_on_exit(&ctx);assert(s_lock_mode==IMAGE_LOCK_ANY);
 }
 assert(!app_image_request_lock_picker(other,true));
 assert(app_image_request_lock_picker(NULL,true));on_enter(&ctx);assert(!s_viewing&&!s_count&&s_lock_mode==IMAGE_LOCK_BOOKMARK);
 image_on_exit(&ctx);assert(app_image_request_open(other));on_enter(&ctx);assert(s_viewing&&s_lock_mode==IMAGE_LOCK_ANY&&image_lock_action_count()==2);
 unsigned returns=lock_style_returns;on_key(&ctx,UI_KEY_2);assert(lock_style_returns==returns);image_on_exit(&ctx);
#endif
 free(s_items);s_items=NULL;
 assert(!remove(path)&&!remove(other));for(int i=0;i<100;++i){snprintf(fixture,sizeof(fixture),"%s/image%03d.jpg",root,i);assert(!remove(fixture));}assert(!rmdir(root));
 puts("PASS: real preview retains all16 gray levels;BW list scope;NULL/OOM/direct paths/siblings/media loss/pixel bounds");
}
"""
for board in ('pico','metalio47'):
    overlay=root/'boards/pico/src/main/apps/app_image.c'
    actual=overlay.read_text() if board=='pico' and overlay.exists() else raw_source
    source=select_source(actual,board)
    source=source.replace('#include \"image_lock_menu.inc\"',(root/'main/apps/image_lock_menu.inc').read_text())
    source=re.sub(r'^#include .*\n','',source,flags=re.M)
    source=re.sub(r'^extern const uint8_t display_test_png_.*\n','',source,flags=re.M)
    with tempfile.TemporaryDirectory() as folder:
        c,binary=Path(folder)/'test.c',Path(folder)/'test'
        c.write_text(prefix+source+tail)
        subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-function',f'-DKIIKO_BOARD_METALIO47={int(board=="metalio47")}','-fsanitize=address,undefined',str(c),str(root/'main/ui/ui_image_dither.c'),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)
        print(board,'verified',flush=True)
