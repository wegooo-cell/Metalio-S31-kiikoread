"""Validate actual S31 low-power pin and rail hooks against the board pin contract."""
from pathlib import Path
import re, subprocess,tempfile
from home_cover_cache_host_test import function
root=Path(__file__).resolve().parents[1]
hw=root/'components/metalio_hw/metalio_hw.c'
unit=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
typedef int esp_err_t;
#define ESP_OK 0
#define GPIO_NUM_6 6
#define GPIO_NUM_7 7
#define ESP_ERR_INVALID_ARG -2
#define GPIO_MODE_INPUT_OUTPUT 3
#define GPIO_PULLUP_DISABLE 0
#define GPIO_PULLDOWN_DISABLE 0
#define GPIO_INTR_DISABLE 0
#define SIG_GPIO_OUT_IDX 256
typedef struct {uint64_t pin_bit_mask;int mode,pull_up_en,pull_down_en,intr_type;} gpio_config_t;
static uint64_t touched,latched,revoked;
static int bad_pin=-1,bad_hold=-1,io_calls,bad_io,io_pins[4];
static uint8_t outputs[2]={0x20,0x14};
static int gpio_hold_dis(int p){touched|=1ULL<<p;latched&=~(1ULL<<p);return 0;}
static int gpio_hold_en(int p){latched|=1ULL<<p;return p==bad_hold?-1:0;}
static void esp_gpio_revoke(uint64_t mask){revoked|=mask;}
static void esp_rom_gpio_connect_out_signal(int p,int sig,bool a,bool b){assert(sig==256&&!a&&!b);touched|=1ULL<<p;}
static int gpio_config(const gpio_config_t *c){assert(c->mode==3&&!c->pull_up_en&&!c->pull_down_en&&!c->intr_type);return c->pin_bit_mask==(1ULL<<bad_pin)?-1:0;}
static int gpio_set_level(int p,int level){assert(!level);touched|=1ULL<<p;return 0;}
static int metalio_io_set(int pin,bool high){assert(io_calls<4);io_pins[io_calls++]=pin;outputs[pin/8]=(outputs[pin/8]&~(1u<<(pin%8)))|((unsigned)high<<(pin%8));return io_calls==bad_io?-1:0;}
'''
unit+='static struct {struct {unsigned sdio_pad_pin_ctrl_ded_sel;} ctrl;\n'
for s in ['clk','cmd','data0','data1','data2','data3']:
    unit+=f'struct {{unsigned sdio_{s}_fun_wpu,sdio_{s}_fun_wpd;}} sdio_{s};\n'
unit+='} CNNT_PAD_CTRL;\n'
unit+=re.search(r'static const int light_sleep_pins\[\]=\{[^}]+\};',hw.read_text())[0]+'\n'
for n in ['metalio_prepare_light_sleep_pins','metalio_hold_for_light_sleep','metalio_release_light_sleep_pins','metalio_sleep_cut_rails','metalio_sleep_restore_rails']:
    unit+=function(n,hw)+'\n'
unit+=r'''
int main(void){
 const uint64_t expected=(1ULL<<4)|(((1ULL<<26)-1)^((1ULL<<8)-1))|(1ULL<<35)|(1ULL<<37)|(1ULL<<40);
 for(int failure=-1;failure<22;failure++){
  touched=latched=revoked=0;bad_pin=failure<0?-1:light_sleep_pins[failure];
  assert((metalio_prepare_light_sleep_pins()==0)==(failure<0));
  assert(touched==expected&&revoked==expected&&!latched);
  assert(!CNNT_PAD_CTRL.ctrl.sdio_pad_pin_ctrl_ded_sel&&CNNT_PAD_CTRL.sdio_clk.sdio_clk_fun_wpd&&!CNNT_PAD_CTRL.sdio_clk.sdio_clk_fun_wpu);
  bad_pin=-1;bad_hold=failure<0?-1:light_sleep_pins[failure];
  assert((metalio_hold_for_light_sleep()==0)==(failure<0));assert(latched==(expected|(1ULL<<6)|(1ULL<<7)));
  metalio_release_light_sleep_pins();assert(latched==((1ULL<<6)|(1ULL<<7)));
  gpio_hold_dis(6);gpio_hold_dis(7);assert(!latched);
 }
 for(int p=6;p<=7;p++){
  bad_hold=p;latched=0;assert(metalio_hold_for_light_sleep()!=ESP_OK);
  metalio_release_light_sleep_pins();gpio_hold_dis(6);gpio_hold_dis(7);
 }
 bad_hold=-1;
 for(int fail=0;fail<=4;fail++){
  uint16_t saved;io_calls=0;bad_io=fail;outputs[0]=0x20;outputs[1]=0x14;
  int cut=metalio_sleep_cut_rails(&saved);assert(saved==0x1420);
  if(cut){bad_io=0;io_calls=0;}else assert(io_calls==2&&io_pins[0]==5&&io_pins[1]==12);
  (void)metalio_sleep_restore_rails(saved);
  assert(outputs[0]==0x20&&outputs[1]==0x14);
  assert(io_pins[io_calls-2]==12&&io_pins[io_calls-1]==5);
 }
 puts("PASS: exact vendor 16 EPD + six SD pins, CNNT release, all22 prepare/hold failures, no GPIO2/36 or LEDC remapping, zero-duty LEDC pads held until authorized light restore, P5/P14 cut and reverse restoration despite I2C faults");
}
'''
# Avoid undefined negative shifts in the fault sentinel.
unit=unit.replace('return c->pin_bit_mask==(1ULL<<bad_pin)?-1:0;', 'return bad_pin>=0 && c->pin_bit_mask==(1ULL<<bad_pin)?-1:0;')
with tempfile.TemporaryDirectory() as d:
    p=Path(d);(p/'test.c').write_text(unit)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
