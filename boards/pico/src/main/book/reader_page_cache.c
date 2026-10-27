/* SPDX-License-Identifier: Apache-2.0
 * 中文：按阅读位置保留上一页和后续页；低内存时只复用已有缓冲或同步绘制。
 * English: Retain previous/future pages around the reader; reuse buffers or draw synchronously on pressure.
 */
#include "reader_page_cache.h"
#include "metalio_memory.h"
#include <stdlib.h>
#include <string.h>
#define FRAME_SLOTS 4
#define FRAME_BYTES_MAX (1024u*1024u)
typedef struct {uint8_t *pixels;size_t page,bytes;uint32_t generation;bool ready,writing;} frame_t;
static frame_t s_frames[FRAME_SLOTS];
static size_t distance(size_t a,size_t b) {return a>b?a-b:b-a;}
const uint8_t *reader_page_cache_find(size_t page,uint32_t generation,size_t bytes) {
    for(unsigned i=0;i<FRAME_SLOTS;++i){
        frame_t *f=&s_frames[i];
        if(f->ready&&f->page==page&&f->generation==generation&&f->bytes==bytes)return f->pixels;
    }
    return NULL;
}
uint8_t *reader_page_cache_begin(size_t page,uint32_t generation,size_t bytes,size_t focus) {
    if(!bytes||bytes>FRAME_BYTES_MAX)return NULL;
    for(unsigned i=0;i<FRAME_SLOTS;++i){
        frame_t *f=&s_frames[i];
        if(f->pixels&&f->page==page&&f->generation==generation&&f->bytes==bytes){
            if(!f->ready)f->writing=true;
            return f->pixels;
        }
    }
    frame_t *chosen=NULL;size_t farthest=0;
    for(unsigned i=0;i<FRAME_SLOTS;++i){
        frame_t *f=&s_frames[i];
        if(f->writing)continue;
        if(!f->ready||f->generation!=generation||f->bytes!=bytes){chosen=f;break;}
        size_t away=distance(f->page,focus);
        if(!chosen||away>farthest){chosen=f;farthest=away;}
    }
    if(!chosen)return NULL;
    if(chosen->bytes!=bytes){free(chosen->pixels);memset(chosen,0,sizeof(*chosen));}
    if(!chosen->pixels){
        if(!metalio_cache_can_grow(bytes))return NULL;
        chosen->pixels=heap_caps_malloc(bytes,METALIO_PSRAM);
        if(!chosen->pixels)return NULL;
    }
    *chosen=(frame_t){chosen->pixels,page,bytes,generation,false,true};
    return chosen->pixels;
}
void reader_page_cache_finish(size_t page,uint32_t generation) {
    for(unsigned i=0;i<FRAME_SLOTS;++i){frame_t *f=&s_frames[i];
        if(f->pixels&&f->page==page&&f->generation==generation&&f->writing){f->writing=false;f->ready=true;return;}}
}
void reader_page_cache_cancel(void) {
    for(unsigned i=0;i<FRAME_SLOTS;++i)if(s_frames[i].writing){s_frames[i].writing=false;s_frames[i].ready=false;}
}
void reader_page_cache_invalidate(void) {
    for(unsigned i=0;i<FRAME_SLOTS;++i){s_frames[i].ready=false;s_frames[i].writing=false;}
}
void reader_page_cache_clear(void) {
    for(unsigned i=0;i<FRAME_SLOTS;++i){free(s_frames[i].pixels);memset(&s_frames[i],0,sizeof(s_frames[i]));}
}
bool reader_page_cache_store(size_t page,uint32_t generation,const uint8_t *pixels,size_t bytes,size_t focus) {
    if(!pixels)return false;
    if(reader_page_cache_find(page,generation,bytes))return true;
    uint8_t *out=reader_page_cache_begin(page,generation,bytes,focus);
    if(!out)return false;
    memcpy(out,pixels,bytes);reader_page_cache_finish(page,generation);return true;
}
size_t reader_page_cache_bytes(void) {
    size_t bytes=0;for(unsigned i=0;i<FRAME_SLOTS;++i)bytes+=s_frames[i].bytes;return bytes;
}
