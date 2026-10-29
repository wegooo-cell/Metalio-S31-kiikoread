#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""中文：Pico两处字体选择器可绘制、选择并翻到128款末项。/ English: Exercise Pico font-picker paint, selection and paging through128 imports."""
from pathlib import Path
import re
import subprocess
import tempfile
from home_cover_cache_host_test import function

root = Path(__file__).resolve().parents[1]
settings = root / 'main/apps/app_device_settings.c'
reader = root / 'main/apps/app_book.c'


def branch(text, marker, after):
    start = text.index(marker, text.index(after))
    scan = re.sub(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"',
                  lambda m: ' ' * len(m[0]), text)
    at = scan.index('{', start) + 1
    depth = 1
    while depth:
        depth += (scan[at] == '{') - (scan[at] == '}')
        at += 1
    return text[start:at]


s = settings.read_text()
r = reader.read_text()
paint = branch(s, 'if (s_page == SETTINGS_SYSTEM_FONT)', 'static void render_content(')
choose = branch(s, 'if (s_page == SETTINGS_SYSTEM_FONT) {', 'static app_redraw_t on_gesture(')
swipe = branch(s, 'if ((s_page == SETTINGS_SYSTEM_FONT || s_page == SETTINGS_WALLPAPER)', 'static app_redraw_t on_gesture(')
reader_choose = branch(r, 'if (s_reader_panel == READER_PANEL_FONT_PICKER)', 'static app_redraw_t reader_panel_action(')
reader_swipe = branch(r, 'if (s_view == READING && s_reader_panel == READER_PANEL_FONT_PICKER &&', 'static app_redraw_t gesture_event(')
layout = s[s.index('typedef struct {\n    EpdRect size, preview;'):s.index('static system_font_layout_t system_font_layout(')]
unit = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "ttf_font.h"
enum{APP_REDRAW_NONE,APP_REDRAW_PAGE,APP_REDRAW_AREA,UI_GESTURE_TAP,UI_GESTURE_SWIPE_U,UI_GESTURE_SWIPE_D,
 SETTINGS_SYSTEM_FONT,SETTINGS_WALLPAPER,READING,READER_PANEL_FONT_PICKER,READER_PANEL_FONT_SETTINGS,UI_ICON_ROTATE_CW};
typedef int app_redraw_t;
typedef struct{int unused;}app_ctx_t;
#define UI_NAV_TOP 1096
#define UI_GRAY_WHITE 255
#define UI_GRAY_BLACK 0
#define SETTINGS_SCROLL_MAX 4000
#define ESP_OK 0
static int count,scale=100,s_font_page,s_main_scroll,s_page=SETTINGS_SYSTEM_FONT,s_wallpaper_page,s_wallpaper_count;
static int s_view=READING,s_reader_panel=READER_PANEL_FONT_PICKER;
static bool s_scroll_present_pending,s_font_sync_confirm,capture_rows;
static char s_notice[96],s_font_sync_path[192],saved[192];
static ttf_font_item_t fonts[TTF_FONT_MAX];
static EpdRect boxes[16];static int rows,selected,previews,restores;
int ttf_font_count(void){return count;}
const ttf_font_item_t*ttf_font_item(int i){assert(i>=0&&i<count);return &fonts[i];}
static unsigned app_settings_system_font_size(void){return scale;}
static void app_settings_set_system_font_size(unsigned n){scale=n;}
static const char*app_settings_system_font_path(void){return saved;}
static const char*app_settings_font_path(void){return "reader.ttf";}
static void app_settings_set_system_font_path(const char*p){snprintf(saved,sizeof(saved),"%s",p);}
static void app_font_activate_system(void){}
static void ui_text_set_system_scale(bool b){(void)b;}
static bool ui_rect_hit(EpdRect q,int x,int y){return x>=q.x&&x<q.x+q.width&&y>=q.y&&y<q.y+q.height;}
static void settings_card(uint8_t*f,EpdRect q,int radius,int fill,int edge){(void)f;(void)radius;(void)fill;(void)edge;
 if(capture_rows){assert(rows<16);boxes[rows++]=q;assert(q.y>=615&&q.y+q.height<UI_NAV_TOP);}}
static void section(uint8_t*f,int y,const char*t){(void)f;(void)y;capture_rows=!strcmp(t,"选择字体");}
static const char*system_font_label(const char*p){return p;}
static void settings_fit_text(char*p,int px,int width){(void)p;(void)px;(void)width;}
static void back_header(uint8_t*f,const char*t){(void)f;(void)t;}
static void settings_navigation(uint8_t*f){(void)f;}
static void draw_system_font_sync(uint8_t*f){(void)f;}
static void ui_text_vc(uint8_t*f,int x,int y,int px,const char*t,int a,bool b){(void)f;(void)x;(void)y;(void)px;(void)t;(void)a;(void)b;}
#define ui_text_fixed_vc ui_text_vc
static void ui_text_box(uint8_t*f,EpdRect q,int px,const char*t,int a,bool b){(void)f;(void)q;(void)px;(void)t;(void)a;(void)b;}
static void ui_draw_icon(uint8_t*f,int x,int y,int px,int i,int gray){(void)f;(void)x;(void)y;(void)px;(void)i;(void)gray;}
static void epd_fill_circle(int x,int y,int radius,int gray,uint8_t*f){(void)x;(void)y;(void)radius;(void)gray;(void)f;}
static void epd_draw_line(int x,int y,int x1,int y1,int gray,uint8_t*f){(void)x;(void)y;(void)x1;(void)y1;(void)gray;(void)f;}
static void draw_sheet(uint8_t*f,int top,const char*t){(void)f;(void)top;(void)t;}
static void ui_fill_round_rect(uint8_t*f,EpdRect q,int radius,int gray){(void)f;(void)radius;(void)gray;
 assert(rows<16);boxes[rows++]=q;assert(q.x>=0&&q.x+q.width<=684&&q.y+q.height<=1216);}
static void ui_draw_control_frame(uint8_t*f,EpdRect q,int radius,int gray){(void)f;(void)q;(void)radius;(void)gray;}
static void copy_text(char*d,size_t n,const char*s){snprintf(d,n,"%s",s);}
static void fit_text(char*p,int px,int w){(void)p;(void)px;(void)w;}
static void fit_fixed_text(char*p,int px,int w){(void)p;(void)px;(void)w;}
static int ui_text_effective_px(int px){return px*scale/100;}
static EpdRect ui_inset_rect(EpdRect q,int n){return(EpdRect){q.x+n,q.y+n,q.width-2*n,q.height-2*n};}
static const char*font_friendly_name(const ttf_font_item_t*p){return p->name;}
const char*ttf_font_path(void){return "builtin";}
const char*ttf_font_display_name(void){return "内建";}
bool ttf_font_is_builtin(void){return true;}
esp_err_t ttf_font_open(const char*p){assert(!strncmp(p,"/fonts/",7));++previews;return ESP_OK;}
esp_err_t ttf_font_open_builtin(void){++restores;return ESP_OK;}
static void draw_font_name_with_current_face(uint8_t*f,int x,int y,const char*t,int w){(void)f;(void)x;(void)y;(void)t;(void)w;}
static void reader_font_choice_finish(void){}
#define reader_panel_text_vc ui_text_vc
static app_redraw_t select_reading_font_item(app_ctx_t*ctx,const ttf_font_item_t*p){(void)ctx;selected=(int)(p-fonts);return APP_REDRAW_PAGE;}
'''
unit += layout
for name in ('settings_viewport_end', 'settings_stacked', 'system_font_layout', 'system_font_item_rect'):
    unit += function(name, settings) + '\n'
unit += 'static void system_paint(void){uint8_t pixel=0;uint8_t*fb=&pixel;' + paint + '}\n'
unit += 'static app_redraw_t system_tap(int x,int y){struct{int x0;}e={x};const typeof(e)*ev=&e;' + choose + 'return APP_REDRAW_NONE;}\n'
unit += 'static app_redraw_t system_swipe(int type){struct{int type;}e={type};const typeof(e)*ev=&e;' + swipe + 'return APP_REDRAW_NONE;}\n'
unit += re.search(r'^#define BOOK_FONT_PAGE .*$', r, re.M)[0] + '\n'
for name in ('reader_font_picker_top', 'reader_font_pick_rect', 'draw_font_picker'):
    unit += function(name, reader) + '\n'
unit += 'static app_redraw_t reader_tap(int x,int y){app_ctx_t c={0};app_ctx_t*ctx=&c;' + reader_choose + 'return APP_REDRAW_NONE;}\n'
unit += 'static app_redraw_t reader_swipe(int type){struct{int type;}e={type};const typeof(e)*ev=&e;' + reader_swipe + 'return APP_REDRAW_NONE;}\n'
unit += r'''
int main(void){
 for(int i=0;i<TTF_FONT_MAX;++i){snprintf(fonts[i].name,sizeof(fonts[i].name),"Font %03d",i);snprintf(fonts[i].path,sizeof(fonts[i].path),"/fonts/Font-%03d.ttf",i);}
 const int counts[]={0,1,24,25,127,128};
 for(scale=100;scale<=200;scale+=10)for(unsigned c=0;c<sizeof(counts)/sizeof(counts[0]);++c){
  count=counts[c];s_font_page=0;s_page=SETTINGS_SYSTEM_FONT;int visited=0;
  do{
   rows=0;capture_rows=false;system_paint();assert(rows>0);
   for(int i=0;i<rows;++i){EpdRect q=boxes[i];int index=s_font_page*system_font_layout().slots+i;
    assert(system_tap(q.x+q.width/2,q.y+q.height/2)==APP_REDRAW_PAGE);
    assert(!strcmp(saved,index?fonts[index-1].path:""));++visited;}
  }while(system_swipe(UI_GESTURE_SWIPE_U)!=APP_REDRAW_NONE);
  assert(visited==count+1);int last=s_font_page;
  assert(system_swipe(UI_GESTURE_SWIPE_U)==APP_REDRAW_NONE&&s_font_page==last);
  while(system_swipe(UI_GESTURE_SWIPE_D)!=APP_REDRAW_NONE){}assert(s_font_page==0);
  s_font_page=0;s_reader_panel=READER_PANEL_FONT_PICKER;visited=0;
  do{
   rows=previews=restores=0;draw_font_picker(NULL);assert(rows==previews&&restores==1);
   for(int i=0;i<rows;++i){EpdRect q=boxes[i];selected=-1;
    assert(reader_tap(q.x+q.width/2,q.y+q.height/2)==APP_REDRAW_PAGE);
    assert(selected==s_font_page*BOOK_FONT_PAGE+i);++visited;}
  }while(reader_swipe(UI_GESTURE_SWIPE_U)!=APP_REDRAW_NONE);
  assert(visited==count);last=s_font_page;
  assert(reader_swipe(UI_GESTURE_SWIPE_U)==APP_REDRAW_NONE&&s_font_page==last);
  while(reader_swipe(UI_GESTURE_SWIPE_D)!=APP_REDRAW_NONE){}assert(s_font_page==0);
 }
 puts("PASS: actual Pico system/reader picker paint,hits and bidirectional paging;0/1/24/25/127/128 imports,11 scales,all128 selectable,no out-of-bounds rows,one-page preview loading and active-face restoration");
}
'''
with tempfile.TemporaryDirectory(prefix='pico-font-picker-') as folder:
    p = Path(folder)
    (p / 'esp_err.h').write_text('#pragma once\ntypedef int esp_err_t;\n')
    (p / 'epdiy.h').write_text('#pragma once\ntypedef struct{int x,y,width,height;}EpdRect;\nenum EpdFontFlags{EPD_DRAW_ALIGN_LEFT,EPD_DRAW_ALIGN_CENTER,EPD_DRAW_ALIGN_RIGHT};\n')
    (p / 'test.c').write_text(unit)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
                    '-fsanitize=address,undefined', '-I' + str(p), '-I' + str(root / 'main/font'),
                    str(p / 'test.c'), '-o', str(p / 'test')], check=True)
    subprocess.run([str(p / 'test')], check=True)
