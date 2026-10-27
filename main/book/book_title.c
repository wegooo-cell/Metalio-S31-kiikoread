/*
 * SPDX-FileCopyrightText: 2026 mindreset
 * SPDX-License-Identifier: Apache-2.0
 *
 * 中文：有界文件名生成显示书名和作者；书名覆盖独立存于NVS，完整路径防止哈希冲突误写。
 * English: Bounded filenames yield display titles/authors; NVS overrides retain full-path collision checks.
 */
#include "book_title.h"
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include "nvs.h"

#define TITLE_PATH_MAX 288
#define TITLE_MAX 120
#define RECORD_MAX (TITLE_PATH_MAX + TITLE_MAX + 8)
#if KIIKO_BOARD_METALIO47
static const char *NS = "mt_titles";
#else
static const char *NS = "rp_titles";
#endif

// 文件名识别只处理内存中的有界片段，不打开EPUB或改写TF文件。
// Parse bounded in-memory spans only, without opening EPUBs or renaming SD files.
typedef struct { const char *p; size_t n; } name_span_t;
static bool name_space(unsigned char c) { return c == ' ' || c == '\t' || c == '\r' || c == '\n'; }
static name_span_t name_trim(name_span_t s) {
    while (s.n && name_space((unsigned char)*s.p)) { ++s.p; --s.n; }
    while (s.n && name_space((unsigned char)s.p[s.n-1])) --s.n;
    return s;
}
static bool name_starts(name_span_t s,const char *prefix) {
    size_t n=strlen(prefix);return s.n>=n&&!strncasecmp(s.p,prefix,n);
}
static size_t name_copy(char *out,size_t cap,name_span_t s) {
    if(!out||!cap)return 0;
    s=name_trim(s);size_t n=s.n<cap?s.n:cap-1;
    while(n<s.n&&n&&((unsigned char)s.p[n]&0xc0)==0x80)--n;
    if(n)memmove(out,s.p,n);
    out[n]=0;return n;
}
// 从尾部配对括号，嵌套作者括号不按第一个右括号截断。
// Pair trailing brackets from the end so nested author names are not split at the first close.
static bool name_group(name_span_t s,name_span_t *body,size_t *start) {
    if(!s.n)return false;
    const char *left=NULL,*right=NULL;size_t width=1;
    switch(s.p[s.n-1]){case ')':left="(";right=")";break;case ']':left="[";right="]";break;
      default:if(s.n>=3&&!memcmp(s.p+s.n-3,"）",3)){left="（";right="）";width=3;}else return false;}
    unsigned depth=0;
    for(size_t i=s.n;i;){
        if(i>=width&&!memcmp(s.p+i-width,right,width)){++depth;i-=width;}
        else if(i>=width&&!memcmp(s.p+i-width,left,width)){
            i-=width;if(!depth)return false;
            if(!--depth){*start=i;*body=name_trim((name_span_t){s.p+i+width,s.n-i-2*width});return true;}
        }else --i;
    }
    return false;
}
static bool name_source_token(name_span_t s) {
    s=name_trim(s);if(name_starts(s,"www.")){s.p+=4;s.n-=4;}
    const char *roots[]={"z-library","z-lib","1lib"};
    for(unsigned i=0;i<sizeof(roots)/sizeof(*roots);++i){
        size_t n=strlen(roots[i]);if(!name_starts(s,roots[i]))continue;
        if(s.n==n)return i<2;
        if(s.p[n]!='.'||s.n==n+1)return false;
        for(size_t j=n+1;j<s.n;++j){unsigned char c=(unsigned char)s.p[j];
            if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='-'||c=='.'))return false;}
        return true;
    }
    return false;
}
static bool name_source(name_span_t s) {
    size_t start=0;bool found=false;
    for(size_t i=0;i<=s.n;++i)if(i==s.n||s.p[i]==','||s.p[i]==';'){
        name_span_t token=name_trim((name_span_t){s.p+start,i-start});
        if(!token.n||!name_source_token(token))return false;
        found=true;start=i+1;
    }
    return found;
}
static bool name_equal(name_span_t a,name_span_t b) {
    a=name_trim(a);b=name_trim(b);size_t i=0,j=0;
    while(i<a.n&&j<b.n){
        if(name_space((unsigned char)a.p[i])){++i;continue;}
        if(name_space((unsigned char)b.p[j])){++j;continue;}
        if(a.p[i++]!=b.p[j++])return false;
    }
    while(i<a.n&&name_space((unsigned char)a.p[i]))++i;
    while(j<b.n&&name_space((unsigned char)b.p[j]))++j;
    return i==a.n&&j==b.n;
}
static bool name_contains(name_span_t s,const char *text) {
    size_t n=strlen(text);if(n>s.n)return false;
    for(size_t i=0;i+n<=s.n;++i)if(!strncasecmp(s.p+i,text,n))return true;
    return false;
}
static bool name_author_candidate(name_span_t s) {
    if(!s.n||s.n>240)return false;
    const char *editions[]={"版","全套","全册","套装","ISBN","edition","volume","illustrated"};
    for(unsigned i=0;i<sizeof(editions)/sizeof(*editions);++i)if(name_contains(s,editions[i]))return false;
    if((name_starts(s,"全")||name_starts(s,"第"))&&(name_contains(s,"册")||name_contains(s,"卷")))return false;
    bool letters=false;for(size_t i=0;i<s.n;++i){unsigned char c=(unsigned char)s.p[i];
        if(c<32||c=='='||c==':'||c==';'||c=='/'||c=='\\')return false;
        if(c>=128||(c>='A'&&c<='Z')||(c>='a'&&c<='z'))letters=true;}
    return letters;
}
static name_span_t name_author(name_span_t s) {
    s=name_trim(s);
    // 明确的“著 … 译”只保留作者，英文别名和国别保留。
    // An explicit authored/translated credit retains the author, English alias and country tag.
    for(size_t i=0;i+3<=s.n;++i)if(!memcmp(s.p+i,"著",3)&&(i+3==s.n||name_space((unsigned char)s.p[i+3]))){s.n=i;break;}
    s=name_trim(s);name_span_t body;size_t at;
    if(name_group(s,&body,&at)&&at&&name_equal((name_span_t){s.p,at},body))s.n=at;
    return name_trim(s);
}
static bool name_has_han(name_span_t s) {
    for(size_t i=0;i+2<s.n;++i){const unsigned char *p=(const unsigned char*)s.p+i;
        if((p[0]&0xf0)==0xe0&&(p[1]&0xc0)==0x80&&(p[2]&0xc0)==0x80){
            unsigned cp=((p[0]&15u)<<12)|((p[1]&63u)<<6)|(p[2]&63u);
            if((cp>=0x3400&&cp<=0x9fff))return true;}
    }
    return false;
}
static name_span_t name_library_title(name_span_t s) {
    // Zlib常把英语原名追加在“ = ”后；中文副标题、卷次和普通文件名保留。
    // Zlib often appends an English parallel title after " = "; retain Chinese subtitles, volumes and ordinary filenames.
    for(size_t i=1;i+1<s.n;++i)if(s.p[i]=='='&&name_space((unsigned char)s.p[i-1])&&name_space((unsigned char)s.p[i+1])){
        name_span_t a=name_trim((name_span_t){s.p,i}),b=name_trim((name_span_t){s.p+i+1,s.n-i-1});
        if(name_has_han(a)&&b.n&&!name_has_han(b)&&((b.p[0]>='A'&&b.p[0]<='Z')||(b.p[0]>='a'&&b.p[0]<='z'))){s=a;break;}
    }
    // 仅去已识别来源中的长宣传尾注；短版本/卷次说明不动。
    // Remove only long promotional tail notes under a recognized source; preserve short edition/volume labels.
    for(size_t i=0;i+6<s.n;++i)if(!memcmp(s.p+i,"【",3)&&s.n-i>=48&&!memcmp(s.p+s.n-3,"】",3)){
        name_span_t note={s.p+i,s.n-i};
        if(name_contains(note,"获奖")||name_contains(note,"畅销")||name_contains(note,"读者")||name_contains(note,"文学奖")){s.n=i;break;}
    }
    return name_trim(s);
}

bool book_name_from_path(const char *path,char *title,size_t title_cap,char *author,size_t author_cap) {
    if(title&&title_cap)title[0]=0;
    if(author&&author_cap)author[0]=0;
    if(!path||!title||!title_cap||strnlen(path,4096)>=4096)return false;
    const char *base=strrchr(path,'/');base=base?base+1:path;
    name_span_t s={base,strlen(base)},auth={0};
    const char *dot=strrchr(base,'.');
    if(dot&&dot!=base&&(!strcasecmp(dot,".epub")||!strcasecmp(dot,".txt")))s.n=(size_t)(dot-base);
    s=name_trim(s);name_span_t candidate=s,body;size_t at;
    // 系统复制的“_副本”不阻碍来源识别，但普通书名中的同字样保持不变。
    // A copied "_副本" suffix may follow a source marker; leave the same text in ordinary titles alone.
    const char *copies[]={"_副本"," 副本"};
    for(unsigned i=0;i<2;++i){size_t n=strlen(copies[i]);if(candidate.n>=n&&!memcmp(candidate.p+candidate.n-n,copies[i],n)){candidate.n-=n;candidate=name_trim(candidate);break;}}
    if(name_group(candidate,&body,&at)&&at&&name_source(body)){
        s=name_trim((name_span_t){candidate.p,at});
        if(name_group(s,&body,&at)&&at&&name_author_candidate(body)){
            auth=name_author(body);s=name_trim((name_span_t){s.p,at});
        }
        s=name_library_title(s);
    }
    if(!s.n)return false;
    name_copy(author,author_cap,auth);
    if(author&&author_cap&&author[0]=='['){
        char *end=strchr(author,']');
        if(end&&end-author<=16){char *next=end+1;while(name_space((unsigned char)*next))++next;
            if(next!=end+1)memmove(end+1,next,strlen(next)+1);}
    }
    return name_copy(title,title_cap,s)>0;
}

bool book_title_from_path(const char *path, char *out, size_t cap) {
    return book_name_from_path(path,out,cap,NULL,0);
}

void book_title_clean_import(char *title) {
    if (!title) return;
    size_t n = strlen(title);
    while (n && (title[n - 1] == ' ' || title[n - 1] == '\t')) title[--n] = 0;
    // 个别 EPUB 转换器把元数据属性片段拼进书名，当前样本的尾巴是“=This”。
    // Some EPUB converters append an attribute fragment; the observed trailing fragment is “=This”.
    if (n >= 5 && !strcasecmp(title + n - 5, "=This")) {
        title[n - 5] = 0;
        n -= 5;
        while (n && (title[n - 1] == ' ' || title[n - 1] == '\t')) title[--n] = 0;
    }
}

static bool valid_utf8(const char *s, size_t max) {
    size_t n = strnlen(s, max + 1);
    if (!n || n > max || s[0] == ' ' || s[n - 1] == ' ') return false;
    for (size_t i = 0; i < n;) {
        uint32_t cp; unsigned more; unsigned char c = (unsigned char)s[i++];
        if (c < 32 || c == 127) return false;
        if (c < 128) continue;
        if (c >= 0xc2 && c <= 0xdf) { cp = c & 31; more = 1; }
        else if (c >= 0xe0 && c <= 0xef) { cp = c & 15; more = 2; }
        else if (c >= 0xf0 && c <= 0xf4) { cp = c & 7; more = 3; }
        else return false;
        unsigned width = more;
        while (more--) {
            if (i == n || ((unsigned char)s[i] & 0xc0) != 0x80) return false;
            cp = (cp << 6) | ((unsigned char)s[i++] & 63);
        }
        if ((width == 2 && cp < 0x800) || (width == 3 && cp < 0x10000) ||
            (cp >= 0xd800 && cp <= 0xdfff) || cp > 0x10ffff) return false;
    }
    return true;
}
static bool path_ok(const char *path) { return path && path[0] && strnlen(path, TITLE_PATH_MAX) < TITLE_PATH_MAX; }
static void key_for(const char *path, char key[11]) {
    uint32_t hash = UINT32_C(2166136261);
    for (const unsigned char *p = (const unsigned char *)path; *p; ++p) hash = (hash ^ *p) * UINT32_C(16777619);
    snprintf(key, 11, "t_%08" PRIx32, hash);
}
static esp_err_t get_record(nvs_handle_t h, const char *key, const char *path, char data[RECORD_MAX], size_t *len) {
    *len = RECORD_MAX;
    esp_err_t err = nvs_get_blob(h, key, data, len);
    if (err != ESP_OK) return err;
    size_t p = strlen(path) + 1;
    if (*len < p + 2 || *len > RECORD_MAX || memcmp(data, path, p) ||
        strnlen(data + p, *len - p) != *len - p - 1) return ESP_ERR_INVALID_STATE;
    return ESP_OK;
}
bool book_title_get(const char *path, char *out, size_t cap) {
    if (!path_ok(path) || !out || !cap) return false;
    out[0] = 0;
    nvs_handle_t h;
    if (nvs_open(NS, NVS_READONLY, &h) != ESP_OK) return false;
    char key[11], data[RECORD_MAX]; size_t len;
    key_for(path, key);
    esp_err_t err = get_record(h, key, path, data, &len);
    nvs_close(h);
    if (err != ESP_OK) return false;
    const char *title = data + strlen(path) + 1;
    if (strlen(title) >= cap) return false;
    strcpy(out, title);
    return true;
}
esp_err_t book_title_set(const char *path, const char *title) {
    if (!path_ok(path) || !title || !valid_utf8(title, TITLE_MAX)) return ESP_ERR_INVALID_ARG;
    nvs_handle_t h;
    esp_err_t err = nvs_open(NS, NVS_READWRITE, &h);
    if (err != ESP_OK) return err;
    char key[11], old[RECORD_MAX]; size_t len;
    key_for(path, key);
    err = get_record(h, key, path, old, &len);
    if (err == ESP_ERR_NVS_NOT_FOUND) err = ESP_OK;
    if (err == ESP_OK) {
        char data[RECORD_MAX];
        size_t p = strlen(path) + 1, t = strlen(title) + 1;
        memcpy(data, path, p); memcpy(data + p, title, t);
        err = nvs_set_blob(h, key, data, p + t);
        if (err == ESP_OK) err = nvs_commit(h);
    }
    nvs_close(h);
    return err;
}
esp_err_t book_title_clear(const char *path) {
    if (!path_ok(path)) return ESP_ERR_INVALID_ARG;
    nvs_handle_t h; esp_err_t err = nvs_open(NS, NVS_READWRITE, &h);
    if (err != ESP_OK) return err;
    char key[11], old[RECORD_MAX]; size_t len;
    key_for(path, key);
    err = get_record(h, key, path, old, &len);
    if (err == ESP_ERR_NVS_NOT_FOUND) err = ESP_OK;
    else if (err == ESP_OK) { err = nvs_erase_key(h, key); if (err == ESP_OK) err = nvs_commit(h); }
    nvs_close(h);
    return err;
}
