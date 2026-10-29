/* SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
 * 中文：有界Liang/TeX英文断词匹配；只读表在Flash，不依赖卡、不分配堆。
 * English: Bounded Liang/TeX English matching with flash-resident tables, no SD access or heap allocation.
 */
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "english_hyphen_patterns.h"
#define ENGLISH_HYPHEN_MAX 63u

// 仅匹配完整ASCII英语词；大写转小写，缩写/数字/非英语字母留给正常整词或紧急换行。
// Match whole ASCII English words, folding case; leave acronyms/numbers/other alphabets to whole-word or emergency wrapping.
static inline bool english_hyphen_points(const char *word,size_t length,uint8_t points[ENGLISH_HYPHEN_MAX+1]) {
    memset(points,0,ENGLISH_HYPHEN_MAX+1);
    if(length<5 || length>ENGLISH_HYPHEN_MAX)return false;
    char prepared[ENGLISH_HYPHEN_MAX+3];prepared[0]='.';unsigned lower=0;
    for(size_t i=0;i<length;++i){
        unsigned char c=(unsigned char)word[i];
        if(c>='a'&&c<='z')++lower;
        else if(c>='A'&&c<='Z')c=(unsigned char)(c+'a'-'A');
        else return false;
        prepared[i+1]=(char)c;
    }
    if(!lower)return false;
    prepared[length+1]='.';prepared[length+2]=0;
    for(size_t i=0;i<sizeof(english_hyphen_exceptions)/sizeof(english_hyphen_exceptions[0]);++i){
        const english_hyphen_exception_t *e=&english_hyphen_exceptions[i];
        if(strlen(e->word)==length && !memcmp(e->word,prepared+1,length)){
            for(size_t cut=2;cut+3<=length;++cut)points[cut]=(uint8_t)((e->points>>cut)&1u);
            return true;
        }
    }
    uint8_t weights[ENGLISH_HYPHEN_MAX+4]={0};
    for(size_t start=0;start<length+2;++start){
        uint16_t node=0;
        for(size_t at=start;at<length+2;++at){
            const english_hyphen_node_t *parent=&english_hyphen_nodes[node];
            unsigned lo=parent->first,hi=lo+parent->count;
            while(lo<hi){unsigned mid=(lo+hi)/2;if(english_hyphen_nodes[mid].letter<(uint8_t)prepared[at])lo=mid+1;else hi=mid;}
            if(lo>=parent->first+parent->count || english_hyphen_nodes[lo].letter!=(uint8_t)prepared[at])break;
            node=(uint16_t)lo;unsigned value=english_hyphen_nodes[node].value;
            if(value){unsigned count=english_hyphen_values[value];
                for(unsigned k=0;k<count;++k)if(english_hyphen_values[value+1+k]>weights[start+k])weights[start+k]=english_hyphen_values[value+1+k];
            }
        }
    }
    for(size_t cut=2;cut+3<=length;++cut)points[cut]=weights[cut+1]&1u;
    return true;
}
