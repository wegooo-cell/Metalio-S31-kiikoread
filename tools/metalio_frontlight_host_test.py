"""Run actual frontlight PWM/settings functions for off-slider, migration and wake faults."""
from pathlib import Path
import re, subprocess, tempfile
root=Path(__file__).resolve().parents[1]
src=(root/'components/metalio_hw/metalio_hw.c').read_text()
def function(name):
    match=re.search(r'^(?:static )?[^\n]+\b'+name+r'\([^;{}]*\)\s*\{',src,re.M)
    assert match,name
    at=match.end();depth=1
    while depth:
        depth+=(src[at]=='{')-(src[at]=='}');at+=1
    return src[match.start():at]+'\n'
unit=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef int esp_err_t;
typedef int nvs_handle_t;
#define ESP_OK 0
#define GPIO_NUM_6 6
#define GPIO_NUM_7 7
static int gpio_hold_dis(int pin){assert(pin==6||pin==7);return 0;}
#define NVS_READONLY 0
#define NVS_READWRITE 1
#define LEDC_LOW_SPEED_MODE 0
#define LEDC_CHANNEL_0 0
#define LEDC_CHANNEL_1 1
#define METALIO_FRONTLIGHT_RANGE 240
static bool fl_ready=true,light_enabled=true,light_dirty;
static uint8_t saved_brightness=30,saved_warmth=50,last_on_brightness=30;
static uint16_t brightness_position=72,warmth_position=120,last_on_position=72;
static unsigned duties[2],updates,writes,commits;
static int fail_open,fail_set,fail_commit;
static struct {uint8_t brightness,warmth,last_on,enabled;unsigned valid;uint16_t brightness_px,warmth_px,last_on_px;} store,pending;
static int key_index(const char *key){
 if(!strcmp(key,"brightness"))return 0;if(!strcmp(key,"warmth"))return 1;
 if(!strcmp(key,"last_on"))return 2;assert(!strcmp(key,"enabled"));return 3;
}
static uint8_t *field(int index, bool staged){
 if(staged){switch(index){case 0:return &pending.brightness;case 1:return &pending.warmth;case 2:return &pending.last_on;default:return &pending.enabled;}}
 switch(index){case 0:return &store.brightness;case 1:return &store.warmth;case 2:return &store.last_on;default:return &store.enabled;}
}
static int nvs_open(const char *name,int mode,nvs_handle_t *h){assert(!strcmp(name,"metalio_light"));if(fail_open)return -1;*h=1;if(mode==NVS_READWRITE)pending=store;return ESP_OK;}
static int nvs_get_u8(nvs_handle_t h,const char *key,uint8_t *value){assert(h==1);int index=key_index(key);if(!(store.valid&(1u<<index)))return -1;*value=*field(index,false);return ESP_OK;}
static int nvs_set_u8(nvs_handle_t h,const char *key,uint8_t value){assert(h==1);++writes;int index=key_index(key);if(fail_set==index+1)return -1;*field(index,true)=value;pending.valid|=1u<<index;return ESP_OK;}
static int fine_index(const char *key){if(!strcmp(key,"brightness_px"))return 4;if(!strcmp(key,"warmth_px"))return 5;assert(!strcmp(key,"last_on_px"));return 6;}
static int nvs_get_u16(nvs_handle_t h,const char *key,uint16_t *out){assert(h==1);int i=fine_index(key);if(!(store.valid&(1u<<i)))return -1;*out=i==4?store.brightness_px:i==5?store.warmth_px:store.last_on_px;return ESP_OK;}
static int nvs_set_u16(nvs_handle_t h,const char *key,uint16_t v){assert(h==1);++writes;int i=fine_index(key);if(fail_set==i+1)return -1;if(i==4)pending.brightness_px=v;else if(i==5)pending.warmth_px=v;else pending.last_on_px=v;pending.valid|=1u<<i;return ESP_OK;}
static int nvs_commit(nvs_handle_t h){assert(h==1);++commits;if(fail_commit)return -1;store=pending;return ESP_OK;}
static void nvs_close(nvs_handle_t h){assert(h==1);}
static int ledc_set_duty(int mode,int channel,unsigned duty){assert(mode==0&&channel>=0&&channel<2&&duty<=511);duties[channel]=duty;return ESP_OK;}
static int ledc_update_duty(int mode,int channel){assert(mode==0&&channel>=0&&channel<2);++updates;return ESP_OK;}
void metalio_frontlight_preview(unsigned,unsigned);
void metalio_frontlight_preview_position(unsigned,unsigned);
void metalio_frontlight_commit(void);
'''
for name in ('metalio_frontlight','metalio_brightness','metalio_warmth','metalio_frontlight_enabled',
             'metalio_frontlight_position','frontlight_apply_position','metalio_frontlight_restore','frontlight_load','metalio_frontlight_save',
             'metalio_frontlight_preview_position',
             'metalio_frontlight_preview','metalio_frontlight_toggle','metalio_frontlight_commit'):
    unit+=function(name)
unit+=r'''
static void reboot(void){saved_brightness=last_on_brightness=30;saved_warmth=50;light_enabled=true;light_dirty=false;duties[0]=duties[1]=999;frontlight_load();metalio_frontlight_restore();}
static void dark(void){assert(!duties[0]&&!duties[1]);}
int main(void){
 store.valid=7;store.brightness=0;store.warmth=70;store.last_on=42;
 reboot();assert(!metalio_frontlight_enabled()&&metalio_brightness()==42&&metalio_warmth()==70);dark();
 // 关闭后全范围调整两个滑块，实际生产PWM始终为零。/ Off sliders stay dark at every value.
 for(unsigned b=0;b<=100;b++)for(unsigned w=0;w<=100;w++){
  metalio_frontlight_preview(b,w);assert(!metalio_frontlight_enabled());dark();
 }
 metalio_frontlight_save(83,15);assert(store.enabled==0&&store.brightness==83&&store.warmth==15&&!light_dirty);
 reboot();assert(!light_enabled&&saved_brightness==83&&saved_warmth==15);dark();
 metalio_frontlight(0,50);metalio_frontlight_restore();dark();
 metalio_frontlight_toggle();assert(light_enabled&&duties[0]>0&&duties[1]>0&&store.enabled==1);
 for(unsigned b=0;b<=100;b++)for(unsigned w=0;w<=100;w++){
  metalio_frontlight_preview(b,w);assert(light_enabled&&duties[0]+duties[1]<=511);
  if(w==0)assert(duties[1]==0);if(w==100)assert(duties[0]==0);if(b==0)dark();
 }
 metalio_frontlight_preview(0,100);metalio_frontlight_commit();assert(light_enabled);reboot();assert(light_enabled&&saved_brightness==0);dark();
 metalio_frontlight_toggle();dark();metalio_frontlight_toggle();assert(saved_brightness==100&&duties[1]==511);
 // 旧版开灯、缺少字段、越界及保存失败。/ Legacy-on, absent/bad values and failed persistence.
 store.valid=7;store.brightness=28;store.warmth=20;store.last_on=42;reboot();assert(light_enabled&&saved_brightness==28&&duties[0]>0);
 store.valid=0;reboot();assert(light_enabled&&saved_brightness==30);
 store.valid=15;store.enabled=9;store.brightness=0;store.last_on=255;store.warmth=255;reboot();assert(!light_enabled&&saved_brightness==30&&saved_warmth==50);dark();
 for(fail_set=1;fail_set<=7;fail_set++){metalio_frontlight_preview(77,20);metalio_frontlight_commit();assert(light_dirty&&!light_enabled);dark();}
 fail_set=0;fail_commit=1;metalio_frontlight_commit();assert(light_dirty);dark();
 fail_commit=0;fail_open=1;metalio_frontlight_commit();assert(light_dirty);dark();
 fail_open=0;metalio_frontlight_commit();assert(!light_dirty&&store.enabled==0&&store.brightness==77);reboot();dark();
 metalio_frontlight_preview(999,999);assert(saved_brightness==100&&saved_warmth==100);dark();
 for(unsigned p=0;p<=240;p++)for(unsigned w=0;w<=240;w++){metalio_frontlight_preview_position(p,w);assert(!light_enabled&&metalio_frontlight_position(false)==p&&metalio_frontlight_position(true)==w);dark();}
 metalio_frontlight_preview_position(121,119);metalio_frontlight_commit();reboot();assert(!light_enabled&&brightness_position==121&&warmth_position==119);dark();
 metalio_frontlight_toggle();assert(light_enabled);metalio_frontlight_preview_position(1,120);assert(saved_brightness==0&&duties[0]==1&&duties[1]==1);metalio_frontlight_commit();reboot();assert(light_enabled&&brightness_position==1);
 metalio_frontlight_toggle();dark();metalio_frontlight_toggle();assert(brightness_position==1);
 metalio_frontlight_preview_position(0,0);metalio_frontlight_toggle();metalio_frontlight_toggle();assert(brightness_position==1);
 puts("PASS: actual PWM off for all slider values, independent switch, legacy settings migration, persistence/reboot/wake, half-scale limit and NVS fault retry");
}
'''
with tempfile.TemporaryDirectory() as d:
    p=Path(d);(p/'test.c').write_text(unit)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
