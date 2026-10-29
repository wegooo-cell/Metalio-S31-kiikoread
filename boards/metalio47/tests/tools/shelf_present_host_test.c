/* SPDX-License-Identifier: Apache-2.0
 * 中文：验证真实同步分区引擎的逐相同时呈现、校准长度、底栏边界、OOM与失败基准。
 * English: Verify simultaneous region phases, calibration length, footer bounds, OOM and failure baselines in the real engine.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define KIIKO_BOARD_METALIO47 1
#include "e0470_page_turn.h"
#include "e0470_epaper_waveform.h"

#define W 1216
#define H 684
#define BYTES (W*H/2)
static uint8_t front[BYTES], back[BYTES], old[BYTES], diff[W*H];
static bool dirty_lines[H];
static uint8_t dirty_columns[W/2];
static EpdiyHighlevelState hl={front,back,diff,dirty_lines,dirty_columns};
static EpdWaveformPhases soft={.phases=48,.luts=(const uint8_t*)"soft"};
static EpdWaveformPhases art={.phases=48,.luts=(const uint8_t*)"art"};
static EpdWaveformPhases cleanup={.phases=48,.luts=(const uint8_t*)"cleanup"};
const EpdWaveform E0470_WAVEFORM={1}, E0470_APPLY_WAVEFORM={2};
static const EpdWaveform soft_wave={3};
static enum EpdRotation rotation=EPD_ROT_INVERTED_PORTRAIT;
static const uint8_t* const* mapped_luts;
static const int *mapped_starts,*mapped_ends;
static const int8_t* mapped_selectors;
static int mapped_count,scans,fail_at,differences,powerons;
static bool full_cleanup,du_chrome,native_area;
static EpdRect expected_area={0,0,H,1120},expected_art={0,192,H,800};
int water_test_alloc_fail;
int epd_width(void){return W;}
int epd_height(void){return H;}
enum EpdRotation epd_get_rotation(void){return rotation;}
EpdRect epd_full_screen(void){return (EpdRect){0,0,W,H};}
void epd_poweron(void){++powerons;}
int64_t esp_timer_get_time(void){return 0;}
void esp_rom_delay_us(uint32_t us){assert(!us);}
const EpdWaveformPhases* e0470_waveform_phases(const EpdWaveform* wave,int mode){
    if(wave==&soft_wave){assert(mode==MODE_GL16||mode==MODE_DU);if(du_chrome&&mode==MODE_GL16)return NULL;assert(mode==(du_chrome?MODE_DU:MODE_GL16));return &soft;}
    assert(wave==&E0470_WAVEFORM);
    assert(mode==MODE_GL16||mode==MODE_GC16);
    return mode==MODE_GC16?&cleanup:&art;
}
void epd_build_1ppB_lut_1k(uint8_t* lut,const EpdWaveformPhases* phases,int phase){
    assert(phase>=0&&phase<phases->phases);
    assert(phases==&soft||phases==&art||phases==&cleanup);
    memset(lut,(phases==&soft?128:0)+phase+1,1024);
}
static int nibble(const uint8_t *fb,int x,int y){return (fb[y*(W/2)+x/2]>>((x&1)*4))&15;}
EpdRect epd_difference_image_cropped(const uint8_t* to,const uint8_t* from,EpdRect area,
    uint8_t* difference,bool* lines,uint8_t* columns){
    assert(to==front&&from==back&&difference==diff&&lines==dirty_lines&&columns==dirty_columns);
    assert(!memcmp(back,old,BYTES));
    assert(area.x==expected_area.y&&area.y==0&&area.width==expected_area.height&&area.height==H);
    ++differences;
    for(int y=0;y<H;++y)for(int x=area.x;x<area.x+area.width;++x)
        diff[y*W+x]=(uint8_t)((nibble(to,x,y)<<4)|nibble(from,x,y));
    return area;
}
void epd_clear_phase_luts(void){mapped_luts=NULL;mapped_selectors=NULL;mapped_count=0;}
void epd_set_line_phase_luts(const uint8_t* const* luts,const int8_t* lines){(void)luts;(void)lines;assert(false);}
void epd_set_col_phase_luts(const uint8_t* const* luts,const int* starts,const int* ends,
    const int8_t* selectors,int count){
    mapped_luts=luts;mapped_starts=starts;mapped_ends=ends;mapped_selectors=selectors;mapped_count=count;
}
enum EpdDrawError epd_draw_base(EpdRect area,const uint8_t* pixels,EpdRect crop,
    enum EpdDrawMode mode,int temperature,const bool* lines,const uint8_t* columns,
    const EpdWaveform* wave){
    assert(area.width==W&&area.height==H&&crop.width==W&&crop.height==H);
    if(native_area){
        assert(mode==(MODE_PACKING_1PPB_DIFFERENCE|MODE_GC16)&&temperature==25&&wave==&E0470_WAVEFORM);
        assert(pixels==diff&&!mapped_luts&&!memcmp(back,old,BYTES));
        for(int y=0;y<H;++y)assert(lines[y]);
        for(int x=0;x<W;++x){
            bool driven=(columns[x/2]>>((x&1)*4))&15;
            assert(driven==(x>=expected_area.y&&x<expected_area.y+expected_area.height));
        }
        ++scans;return fail_at?EPD_DRAW_OTHER_ERROR:EPD_DRAW_SUCCESS;
    }
    assert(mode==(MODE_PACKING_1PPB_DIFFERENCE|MODE_DU)&&temperature==25&&wave==&E0470_APPLY_WAVEFORM);
    assert(pixels==diff&&lines==dirty_lines&&columns==dirty_columns);
    assert(mapped_luts&&mapped_count==3&&!memcmp(back,old,BYTES));
    assert(mapped_starts[0]==(expected_area.y&~31)&&mapped_ends[0]==expected_art.y);
    assert(mapped_starts[1]==expected_art.y&&mapped_ends[1]==expected_art.y+expected_art.height);
    assert(mapped_starts[2]==mapped_ends[1]&&mapped_ends[2]==((expected_area.y+expected_area.height+31)&~31));
    for(int y=0;y<H;++y)assert(lines[y]);
    for(int x=0;x<W;++x)assert(!!columns[x/2]==(x>=expected_area.y&&x<expected_area.y+expected_area.height));
    for(int y=0;y<H;y+=83){
        // 每一相均覆盖题头/中部/分页，输入必须来自同一真实前后帧。
        // Every phase covers header/art/pagination using the same real prior/target pair.
        const int points[]={0,1,159,160,161,191,192,193,991,992,993,1087,1088,1097,1101,1119};
        for(unsigned i=0;i<sizeof(points)/sizeof(points[0]);++i){int x=points[i];if(x<expected_area.y||x>=expected_area.y+expected_area.height)continue;assert(diff[y*W+x]==((nibble(front,x,y)<<4)|nibble(old,x,y)));}
    }
    for(int band=0;band<3;++band){
        assert(mapped_selectors[band]==(band==1?1:0));
        int expected=band==1?(scans<(full_cleanup?cleanup.phases:art.phases)?scans+1:0):
            scans<soft.phases?129+scans:0;
        for(int i=0;i<1024;++i)assert(mapped_luts[mapped_selectors[band]][i]==expected);
    }
    ++scans;
    return fail_at==scans?EPD_DRAW_OTHER_ERROR:EPD_DRAW_SUCCESS;
}
static void reset(void){
    scans=differences=powerons=fail_at=0;water_test_alloc_fail=0;
    epd_clear_phase_luts();rotation=EPD_ROT_INVERTED_PORTRAIT;
    for(int i=0;i<BYTES;++i){old[i]=back[i]=(uint8_t)(i*13);front[i]=(uint8_t)(i*17+5);}
}
enum EpdDrawError epd_draw_base_from_phase(EpdRect a,const uint8_t *d,EpdRect c,enum EpdDrawMode m,
    int t,const bool *l,const uint8_t *cols,const EpdWaveform *w,int p){
    (void)a;(void)d;(void)c;(void)m;(void)t;(void)l;(void)cols;(void)w;(void)p;assert(false);return EPD_DRAW_NO_PHASES_AVAILABLE;
}
static enum EpdDrawError run(void){
    return e0470_update_regions(&hl,expected_area,expected_art,&soft_wave,&E0470_WAVEFORM,full_cleanup?MODE_GC16:MODE_GL16);
}
int main(void){
    for(int layout=0;layout<3;++layout)for(int gc=0;gc<3;++gc)for(int fail=0;fail<=48;++fail){
        expected_art=layout==2?(EpdRect){0,0,H,1088}:layout?(EpdRect){0,160,H,928}:(EpdRect){0,192,H,800};
        reset();full_cleanup=gc!=0;cleanup.phases=gc==2?47:48;fail_at=fail;
        assert(run()==(fail?EPD_DRAW_OTHER_ERROR:EPD_DRAW_SUCCESS));
        assert(scans==(fail?fail:48)&&differences==1&&powerons==1&&!mapped_luts);
        for(int y=0;y<H;++y)for(int x=0;x<W;++x){
            bool committed=!fail&&x>=expected_area.y&&x<expected_area.y+expected_area.height;
            assert(nibble(back,x,y)==nibble(committed?front:old,x,y));
        }
    }
    // 真实分区引擎覆盖37相及跨主页两拍补白后的39相；每个失败相均不得提交半帧。
    // Exercise real37/39-phase regional scans; every failed phase must preserve the prior framebuffer.
    expected_art=(EpdRect){0,192,H,800};full_cleanup=false;
    for(int phases=37;phases<=39;phases+=2)for(int failure=0;failure<=phases;++failure){
        soft.phases=art.phases=phases;reset();fail_at=failure;
        assert(run()==(failure?EPD_DRAW_OTHER_ERROR:EPD_DRAW_SUCCESS));
        assert(scans==(failure?failure:phases)&&differences==1&&powerons==1&&!mapped_luts);
        for(int y=0;y<H;++y)for(int x=0;x<W;++x){
            bool committed=!failure&&x<expected_area.height;
            assert(nibble(back,x,y)==nibble(committed?front:old,x,y));
        }
    }
    expected_art=(EpdRect){0,544,H,544};full_cleanup=false;
    for(int failure=0;failure<=52;++failure){
        soft.phases=50;art.phases=52;reset();fail_at=failure;
        assert(run()==(failure?EPD_DRAW_OTHER_ERROR:EPD_DRAW_SUCCESS));
        assert(scans==(failure?failure:52)&&differences==1&&powerons==1&&!mapped_luts);
        for(int y=0;y<H;++y)for(int x=0;x<W;++x){
            bool committed=!failure&&x<expected_area.height;
            assert(nibble(back,x,y)==nibble(committed?front:old,x,y));
        }
    }
    // DU14和完整灰阶同时逐相输出，短表结束后全保持；逐拍失败不提交back。
    // DU14 and complete grays run together, holding after the shorter table ends; no failed phase commits back.
    expected_art=(EpdRect){0,352,H,672};full_cleanup=false;du_chrome=true;
    for(int failure=0;failure<=58;++failure){
        soft.phases=22;art.phases=58;reset();fail_at=failure;
        assert(run()==(failure?EPD_DRAW_OTHER_ERROR:EPD_DRAW_SUCCESS));
        assert(scans==(failure?failure:58)&&differences==1&&powerons==1&&!mapped_luts);
        for(int y=0;y<H;++y)for(int x=0;x<W;++x){
            bool committed=!failure&&x<expected_area.height;
            assert(nibble(back,x,y)==nibble(committed?front:old,x,y));
        }
    }
    du_chrome=false;
    // 列表GC精确到未对齐/奇数半字节边缘，等值像素也驱动；失败不提交，且无需PSRAM分配。
    // List GC uses exact unaligned/odd nibble edges and drives equal pixels; failures do not commit and no PSRAM allocation is needed.
    native_area=true;
    const EpdRect list_crops[]={{0,160,H,928},{0,190,H,898},{0,191,H,896},{0,191,H,897}};
    for(unsigned c=0;c<sizeof(list_crops)/sizeof(list_crops[0]);++c)for(int fail=0;fail<2;++fail){
        reset();expected_area=list_crops[c];fail_at=fail;water_test_alloc_fail=1;
        assert(e0470_update_native_area(&hl,expected_area,&E0470_WAVEFORM)==(fail?EPD_DRAW_OTHER_ERROR:EPD_DRAW_SUCCESS));
        assert(scans==1&&differences==1&&powerons==1&&!mapped_luts);
        for(int y=0;y<H;++y)for(int x=0;x<W;++x){
            bool committed=!fail&&x>=expected_area.y&&x<expected_area.y+expected_area.height;
            assert(nibble(back,x,y)==nibble(committed?front:old,x,y));
        }
    }
    native_area=false;expected_area=(EpdRect){0,0,H,1120};
    // 灰阶列表上八白/下十白同轮，190像素的精确裁剪不触及题头，逐拍失败保持back。
    // List strengths share one scan; exact190px crops protect the header and all failed phases preserve back.
    expected_area=(EpdRect){0,190,H,898};expected_art=(EpdRect){0,640,H,448};full_cleanup=false;
    for(int failure=0;failure<=60;++failure){
        soft.phases=58;art.phases=60;reset();fail_at=failure;
        assert(run()==(failure?EPD_DRAW_OTHER_ERROR:EPD_DRAW_SUCCESS));
        for(int y=0;y<H;++y)for(int x=0;x<W;++x){
            bool commit=!failure&&x>=190&&x<1088;
            assert(nibble(back,x,y)==nibble(commit?front:old,x,y));
        }
    }
    expected_area=(EpdRect){0,0,H,1120};
    soft.phases=art.phases=48;
    expected_art=(EpdRect){0,192,H,800};
    reset();water_test_alloc_fail=1;assert(run()==EPD_DRAW_NO_PHASES_AVAILABLE);
    assert(!scans&&!differences&&!powerons&&!memcmp(old,back,BYTES));
    const EpdRect invalid[]={{0,0,H,1119},{1,0,H,1120},{0,-32,H,1120},{0,0,H,2147483647},{0,1184,H,64}};
    for(unsigned i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i){
        reset();EpdRect valid=expected_area;expected_area=invalid[i];
        assert(run()==EPD_DRAW_INVALID_CROP);expected_area=valid;
        assert(!scans&&!differences&&!powerons);
    }
    const EpdRect invalid_art[]={{0,193,H,800},{0,192,H,801},{0,992,H,160},{1,192,H,800},{0,192,H,2147483647}};
    for(unsigned i=0;i<sizeof(invalid_art)/sizeof(invalid_art[0]);++i){
        reset();EpdRect valid=expected_art;expected_art=invalid_art[i];
        assert(run()==EPD_DRAW_INVALID_CROP);expected_art=valid;
        assert(!scans&&!differences&&!powerons);
    }
    for(int rot=0;rot<3;++rot){reset();rotation=rot;assert(run()==EPD_DRAW_INVALID_CROP);assert(!scans);}
    puts("simultaneous BW/gray up to58 phases and exact native-GC list crops; shelf37/39/48 phases, shared chrome/art, GC48/47 padding, footer, every phase failure, OOM and geometry passed");
    return 0;
}
