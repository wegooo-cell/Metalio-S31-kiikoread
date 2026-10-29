/* SPDX-FileCopyrightText: 2026 mindreset
 * SPDX-License-Identifier: Apache-2.0
 * 中文：TXT 与 EPUB 单实例书源分派，不依赖界面。
 * English: Singleton TXT and EPUB source dispatch without UI dependencies.
 * 冻结：TXT 保留源字节偏移，EPUB 采用累计 spine HTML 字节；兼容纯文本加载，不写文件。
 * Frozen: TXT retains source offsets; EPUB uses cumulative spine HTML bytes; retain plain-text loading and never write files.
 */
#include "book_source_internal.h"
#include "book_epub.h"
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#if KIIKO_BOARD_METALIO47
#include <sys/stat.h>
#else
#endif
static book_txt_t s_book;
static book_epub_t *s_epub;
#if KIIKO_BOARD_METALIO47
static char s_io_path[512];
static bool s_io_suspended;
static struct stat s_io_stat;
#else
#endif
esp_err_t book_open(const char *path) {
    book_close();
#if KIIKO_BOARD_METALIO47
    if (!path || !*path || strlen(path) >= sizeof(s_io_path)) return ESP_ERR_INVALID_ARG;
    snprintf(s_io_path, sizeof(s_io_path), "%s", path);
#else
    if (!path || !*path) return ESP_ERR_INVALID_ARG;
#endif
    const char *ext = strrchr(path, '.');
    if (ext && !strcasecmp(ext, ".epub")) return book_epub_open(path, &s_epub);
    if (!ext || strcasecmp(ext, ".txt")) return ESP_ERR_NOT_SUPPORTED;
    esp_err_t err = book_txt_open(&s_book, path);
    if (err != ESP_OK) book_close();
    return err;
}
void book_close(void) {
#if KIIKO_BOARD_METALIO47
    s_io_suspended = false; s_io_path[0] = 0;
#else
#endif
    book_epub_close(s_epub); s_epub = NULL;
    book_txt_close(&s_book);
}
void book_set_embedded_fonts(bool on) {
    if (s_epub) book_epub_set_fonts_enabled(s_epub, on);
}
size_t book_chapter_count(void) { return s_epub ? book_epub_chapter_count(s_epub) : s_book.count; }
size_t book_navigation_count(void) {
    return s_epub ? book_epub_navigation_count(s_epub) : s_book.nav_count?s_book.nav_count:s_book.count;
}
size_t book_navigation_chapter(size_t position) {
    return s_epub ? book_epub_navigation_chapter(s_epub, position) :
                    s_book.nav_count?book_txt_nav_chapter(&s_book,position):position<s_book.count?position:SIZE_MAX;
}
esp_err_t book_navigation_title(size_t position, char *buf, size_t cap) {
    if (s_epub) return book_epub_navigation_title(s_epub, position, buf, cap);
    return s_book.nav_count?book_txt_title(&s_book,position,true,buf,cap):book_chapter_title(position,buf,cap);
}
const char *book_navigation_anchor(size_t position) {
    return s_epub ? book_epub_navigation_anchor(s_epub, position) : NULL;
}
size_t book_navigation_source_offset(size_t position) {
    return s_epub ? book_epub_navigation_source_offset(s_epub, position) :
        s_book.nav_count?book_txt_nav_source_offset(&s_book,position):SIZE_MAX;
}
size_t book_navigation_position(size_t chapter,size_t text_offset) {
    return s_epub?SIZE_MAX:book_txt_nav_position(&s_book,chapter,text_offset);
}
size_t book_navigation_volume_count(void) { return s_epub?0:s_book.volume_count; }
bool book_navigation_volume(size_t index,book_volume_t *out) {
    if(s_epub || !out || index>=s_book.volume_count)return false;
    const book_txt_volume_t *v=&s_book.volumes[index];
    *out=(book_volume_t){v->begin,v->end,v->title==UINT16_MAX?SIZE_MAX:v->title,v->number};
    return true;
}
size_t book_navigation_volume_for(size_t position) {
    if(s_epub || !s_book.volume_count || position>=s_book.nav_count)return SIZE_MAX;
    size_t lo=0,hi=s_book.volume_count;
    while(lo+1<hi){size_t mid=lo+(hi-lo)/2;if(s_book.volumes[mid].begin<=position)lo=mid;else hi=mid;}
    return lo;
}
esp_err_t book_navigation_volume_title(size_t index,char *buf,size_t cap) {
    book_volume_t v;
    if(!buf || !cap || !book_navigation_volume(index,&v))return ESP_ERR_INVALID_ARG;
    if(v.title!=SIZE_MAX)return book_navigation_title(v.title,buf,cap);
    int n=v.number?snprintf(buf,cap,"第 %u 卷",v.number):snprintf(buf,cap,"卷首内容");
    return n>=0&&(size_t)n<cap?ESP_OK:ESP_ERR_INVALID_SIZE;
}
esp_err_t book_chapter_title(size_t i, char *buf, size_t cap) {
    if (s_epub) return book_epub_chapter_title(s_epub, i, buf, cap);
    return book_txt_title(&s_book,i,false,buf,cap);
}
esp_err_t book_chapter_load(size_t i, char **utf8, size_t *len) {
    if (!utf8 || !len) return ESP_ERR_INVALID_ARG;
    *utf8 = NULL; *len = 0;
    if (s_epub) {
        html_text_t text = {0}; esp_err_t err = book_epub_load(s_epub, i, &text);
        if (err != ESP_OK) return err;
        *utf8 = text.utf8; *len = text.len; text.utf8 = NULL;
        html_text_free(&text); return ESP_OK;
    }
    if (!s_book.file || i >= s_book.count) return ESP_ERR_INVALID_ARG;
    return book_txt_load(&s_book, i, utf8, len);
}
esp_err_t book_chapter_load_blocks(size_t i, html_text_t *out) {
    if (!out) return ESP_ERR_INVALID_ARG;
    memset(out, 0, sizeof(*out));
    if (s_epub) return book_epub_load(s_epub, i, out);
    return book_chapter_load(i, &out->utf8, &out->len);
}
esp_err_t book_chapter_load_blocks_anchor(size_t i, const char *anchor,
                                           size_t *anchor_offset, html_text_t *out) {
    return book_chapter_load_blocks_target(i, anchor, SIZE_MAX, anchor_offset, out);
}
esp_err_t book_chapter_load_blocks_target(size_t i, const char *anchor,
                                           size_t source_offset, size_t *text_offset,
                                           html_text_t *out) {
    if (text_offset) *text_offset = 0;
    if (s_epub) return book_epub_load_target(s_epub, i, anchor, source_offset, text_offset, out);
    if(!out)return ESP_ERR_INVALID_ARG;
    memset(out,0,sizeof(*out));
    return book_txt_load_target(&s_book,i,source_offset,text_offset,&out->utf8,&out->len);
}
uint32_t book_total_bytes(void) { return s_epub ? book_epub_total_bytes(s_epub) : s_book.total; }
uint32_t book_chapter_byte_offset(size_t i) {
    return s_epub ? book_epub_chapter_byte_offset(s_epub, i) : i < s_book.count ? s_book.entries[i].offset : 0;
}
book_kind_t book_kind(void) { return s_epub ? BOOK_KIND_EPUB : BOOK_KIND_TXT; }
#if KIIKO_BOARD_METALIO47
int book_chapter_prefetch_step(size_t chapter) {
    return s_epub?book_epub_prefetch_step(s_epub,chapter):-1;
}
#else
#endif
esp_err_t book_chapter_image(size_t chapter, const char *src, uint8_t **data, size_t *size, bool *png) {
    return s_epub ? book_epub_image(s_epub, chapter, src, data, size, png) : ESP_ERR_NOT_SUPPORTED;
}

esp_err_t book_chapter_image_dimensions(size_t chapter, const char *src, unsigned *width, unsigned *height) {
    return s_epub ? book_epub_image_dimensions(s_epub, chapter, src, width, height) : ESP_ERR_NOT_SUPPORTED;
}
#if KIIKO_BOARD_METALIO47

esp_err_t book_suspend_io(void) {
    if (s_epub) return book_epub_suspend_io(s_epub);
    if (!s_book.file || s_io_suspended) return ESP_OK;
    if (fstat(fileno(s_book.file), &s_io_stat)) return ESP_FAIL;
    int result = fclose(s_book.file);
    s_book.file = NULL; s_io_suspended = true;
    return result ? ESP_FAIL : ESP_OK;
}
esp_err_t book_resume_io(void) {
    if (s_epub) return book_epub_resume_io(s_epub);
    if (!s_io_suspended) return ESP_OK;
    FILE *file = fopen(s_io_path, "rb");
    struct stat now;
    if (!file || fstat(fileno(file), &now) || now.st_size != s_io_stat.st_size ||
        now.st_mtime != s_io_stat.st_mtime) {
        if (file) fclose(file);
        return ESP_FAIL;
    }
    s_book.file = file; s_io_suspended = false;
    return ESP_OK;
}
// EPUB恢复由其ZIP对象管理；非空EPUB保守地视为仍需媒体。
// EPUB owns its ZIP state; conservatively require media while that object exists.
bool book_io_pending(void) { return s_io_suspended || s_epub != NULL; }
#else
#endif
