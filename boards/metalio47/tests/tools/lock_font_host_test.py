"""票根字体上下文与浅睡恢复，使用真实切换函数。/ Actual ticket font switching and light-wake restoration.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import subprocess
import tempfile
from home_cover_cache_host_test import function
ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / 'main/font/app_font_context.c'
unit = r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
typedef int esp_err_t;
#define ESP_ERR_INVALID_RESPONSE 0x108
static int64_t s_rejected_retry_us,clock_us;
static unsigned s_rejected_attempts;
static int64_t esp_timer_get_time(void){return clock_us;}
static unsigned transient_failures;
static bool media_ready=true;
static bool wake_pending;
static bool app_sleep_media_pending(void){return wake_pending;}
static bool read_pico_sd_io_ready(void){return media_ready;}
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#define ESP_OK 0
#define TTF_FONT_PATH_MAX 288
#define TTF_FONT_BUILTIN "builtin"
typedef struct {char path[288];bool reading;} app_lock_font_t;
typedef struct {char path[288];} ttf_font_item_t;
static bool s_reading,system_face,system_scale,recovery;
static char s_rejected[TTF_FONT_PATH_MAX],corrupt[288];
static time_t s_rejected_mtime;
static off_t s_rejected_size;
static int stroke,reading_weight=2;
static int app_settings_book_weight_fine(void){return reading_weight;}
static void ttf_set_stroke_adjust_fine(int level){stroke=level;}
static void ttf_set_stroke_adjust(int level){stroke=level*16;}
static bool reading_aa=false,aa=true;
static bool app_settings_book_antialias(void){return reading_aa;}
static void ttf_set_antialias(bool enabled){aa=enabled;}
static char chosen[288]="/fonts/system.ttf",reader[288]="/fonts/reader.ttf",active[288]="builtin",missing[288];
static unsigned opens;
static int mock_stat(const char *path,struct stat *st){
 if(!*path || !strncmp(path,"/absent/",8) || !strcmp(path,missing))return -1;
 memset(st,0,sizeof(*st));st->st_mode=S_IFREG;st->st_size=100;st->st_mtime=1;return 0;
}
#define stat(path,st) mock_stat(path,st)
static bool pico_boot_recovery(void){return recovery;}
static const char *app_settings_system_font_path(void){return chosen;}
static const char *app_settings_font_path(void){return reader;}
static const char *app_settings_fonts_dir(void){return "/absent/fonts";}
static bool ttf_font_ready(void){return true;}
static const char *ttf_font_path(void){return active;}
static bool ttf_font_is_builtin(void){return !strcmp(active,"builtin");}
static bool ttf_font_path_is_builtin(const char *path){return !*path||!strcmp(path,"builtin");}
static int ttf_font_count(void){return 0;}
static void ttf_font_scan(void){}
static const ttf_font_item_t *ttf_font_item(int index){(void)index;return NULL;}
static int ttf_font_open(const char *path){++opens;if(!strcmp(path,corrupt)){active[0]=0;return ESP_ERR_INVALID_RESPONSE;}
 if(!strcmp(path,reader)&&transient_failures){--transient_failures;strcpy(active,"builtin");return -1;}
 if(!strcmp(path,missing)){active[0]=0;return -1;}snprintf(active,sizeof(active),"%s",path);return ESP_OK;}
static int ttf_font_open_builtin(void){return ttf_font_open("builtin");}
static void ui_text_set_system_font(bool on){system_face=on;}
static void ui_text_set_system_scale(bool on){system_scale=on;}
static void ui_nav_status_font_context(bool reading,bool changed){(void)changed;assert(reading==s_reading);}
'''
for name in ('font_file', 'system_path', 'activate', 'app_font_activate_system', 'app_font_activate_reading',
             'app_font_retry_active', 'app_font_recover_media', 'app_font_begin_lock', 'app_font_end_lock'):
    unit += function(name, FONT) + '\n'
unit += r'''
int main(void){
 app_lock_font_t saved;
 // 有意卸载期间不能打开文件/换内建；重新就绪后保持原选择可恢复。
 // Intentional unmount cannot open files or select built-in; the same choice recovers when ready.
 strcpy(active,reader);s_reading=true;media_ready=false;unsigned paused=opens;
 app_font_begin_lock(&saved);app_font_end_lock(&saved);
 assert(opens==paused&&!strcmp(active,reader)&&s_reading);
 // Cached mount success must not bypass an outstanding wake recovery transaction.
 media_ready=true;wake_pending=true;strcpy(active,reader);s_reading=true;paused=opens;
 app_font_begin_lock(&saved);app_font_end_lock(&saved);assert(opens==paused&&!strcmp(active,reader));
 wake_pending=false;strcpy(active,"builtin");s_reading=false;
 // 缺失字体可重复尝试，但不会重载内建或报告变化。/ Retry missing fonts without reloading built-in or reporting changes.
 strcpy(missing,chosen);unsigned first=opens;
 assert(!app_font_activate_system()&&ttf_font_is_builtin()&&opens==first);
 assert(!app_font_retry_active()&&ttf_font_is_builtin()&&opens==first);
 missing[0]=0;assert(app_font_retry_active()&&!strcmp(active,chosen));
 assert(!app_font_retry_active());

 app_font_activate_reading();assert(s_reading&&!system_face&&!system_scale&&!strcmp(active,reader)&&stroke==reading_weight&&!aa);
 app_font_begin_lock(&saved);assert(!s_reading&&system_face&&system_scale&&!strcmp(active,chosen)&&stroke==0&&aa);
 assert(saved.reading&&!strcmp(saved.path,reader));
 app_font_end_lock(&saved);assert(s_reading&&!system_face&&!system_scale&&!strcmp(active,reader)&&stroke==reading_weight&&!aa);
 app_font_activate_system();unsigned before=opens;
 app_font_begin_lock(&saved);assert(!s_reading&&system_face&&system_scale&&!strcmp(active,chosen)&&stroke==0);
 app_font_end_lock(&saved);assert(!s_reading&&system_face&&system_scale&&!strcmp(active,chosen)&&opens==before);
 app_font_activate_reading();app_font_begin_lock(&saved);strcpy(missing,reader);
 app_font_end_lock(&saved);assert(s_reading&&!system_face&&!system_scale&&ttf_font_is_builtin());
 strcpy(missing,chosen);app_font_begin_lock(&saved);assert(ttf_font_is_builtin()&&!system_face&&system_scale);
 assert(!strcmp(chosen,"/fonts/system.ttf")&&!strcmp(reader,"/fonts/reader.ttf"));
 app_font_end_lock(&saved);assert(s_reading&&!system_face&&!system_scale);
 missing[0]=chosen[0]=0;app_font_begin_lock(&saved);assert(ttf_font_is_builtin()&&!system_face&&system_scale);
 app_font_end_lock(&saved);assert(s_reading&&!system_scale);
 // Imported reading face disappears while already active: fallback once and remain stable.
 strcpy(reader,"/fonts/reader.ttf");missing[0]=0;app_font_activate_reading();strcpy(missing,reader);
 assert(app_font_retry_active()&&ttf_font_is_builtin());before=opens;
 for(int i=0;i<100;++i)assert(!app_font_retry_active()&&opens==before);
 missing[0]=0;assert(app_font_retry_active());strcpy(corrupt,reader);active[0]=0;
 assert(app_font_retry_active()&&ttf_font_is_builtin());before=opens;
 for(int i=0;i<100;++i)assert(!app_font_retry_active()&&opens==before);
 // 手动重新加载同一文件立即解除旧拒绝，毋须改名或重启。/ Manual reloading clears old rejection without renaming/reboot.
 corrupt[0]=0;assert(ttf_font_open(reader)==ESP_OK);assert(!app_font_retry_active()&&!s_rejected[0]);
 active[0]=0;transient_failures=1;assert(app_font_retry_active()&&ttf_font_is_builtin());before=opens;
 for(int i=0;i<100;++i)assert(!app_font_retry_active()&&opens==before);
 clock_us+=1000000;assert(app_font_retry_active()&&!strcmp(active,reader)&&!s_rejected[0]);
 active[0]=0;transient_failures=4;assert(app_font_retry_active());
 const int64_t delays[]={1000000,3000000,10000000,30000000};
 for(unsigned i=0;i<4;++i){before=opens;clock_us+=delays[i]-1;assert(!app_font_retry_active()&&opens==before);
 ++clock_us;assert(app_font_retry_active()||ttf_font_is_builtin());}
 assert(!strcmp(active,reader)&&!s_rejected[0]);
 strcpy(chosen,"/fonts/system.ttf");app_font_activate_system();strcpy(missing,chosen);
 assert(app_font_retry_active()&&ttf_font_is_builtin());before=opens;
 for(int i=0;i<100;++i)assert(!app_font_retry_active()&&opens==before);
 missing[0]=0;
 strcpy(chosen,"/fonts/system.ttf");recovery=true;
 app_font_begin_lock(&saved);assert(ttf_font_is_builtin()&&!system_face);app_font_end_lock(&saved);
 app_font_begin_lock(NULL);app_font_end_lock(NULL);
 // Manual recovery clears transient file backoff, while abnormal-boot builtin protection remains.
 recovery=false;strcpy(s_rejected,chosen);s_rejected_size=100;s_rejected_mtime=1;
 s_rejected_retry_us=clock_us+30000000;strcpy(active,"builtin");
 assert(!app_font_retry_active()&&ttf_font_is_builtin());
 assert(app_font_recover_media()&&!strcmp(active,chosen)&&!s_rejected[0]&&!s_rejected_retry_us);
 recovery=true;strcpy(active,"builtin");strcpy(s_rejected,chosen);
 assert(!app_font_recover_media()&&ttf_font_is_builtin()&&!strcmp(chosen,"/fonts/system.ttf"));
 puts("PASS: ticket/wake font contexts, paused IO, manual retry clears transient rejection, abnormal boot protection and saved choices retained");
}
'''
with tempfile.TemporaryDirectory(dir=ROOT / 'build') as folder:
    c, exe = Path(folder) / 'test.c', Path(folder) / 'test'
    c.write_text(unit)
    subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined',
                    str(c), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
