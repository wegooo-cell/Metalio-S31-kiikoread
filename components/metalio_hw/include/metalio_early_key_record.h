/* SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
 * One-use S31 bootloader -> application physical-key evidence, in app-owned RTC noinit.
 * No NVS writes, no reset-reason override and no persistent unlock permission.
 */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <string.h>

#define METALIO_EARLY_KEY_MAGIC UINT32_C(0x314b5053)
#define METALIO_EARLY_KEY_BOARD UINT32_C(0x00310015)
#define METALIO_EARLY_KEY_POWERON 1u
#define METALIO_EARLY_KEY_VALID 1u
#define METALIO_EARLY_KEY_PRESSED 2u
#define METALIO_EARLY_KEY_DESC_MAGIC UINT32_C(0x31444b53)
typedef struct {
    uint32_t magic,version,board,address,size,reserved;
} metalio_early_key_app_desc_t;
typedef struct {
    uint32_t magic, version, board, reason, flags, samples, config, checksum;
} metalio_early_key_record_t;
_Static_assert(sizeof(metalio_early_key_record_t) == 32, "RTC key protocol size");
_Static_assert(sizeof(metalio_early_key_app_desc_t) == 24, "Image key descriptor size");

static inline bool metalio_early_key_descriptor_valid(const metalio_early_key_app_desc_t *desc,
        uintptr_t rtc_low,uintptr_t rtc_high) {
    return desc->magic==METALIO_EARLY_KEY_DESC_MAGIC && desc->version==1 &&
        desc->board==METALIO_EARLY_KEY_BOARD && desc->size==sizeof(metalio_early_key_record_t) &&
        !desc->reserved && !(desc->address&3) &&
        rtc_high>=rtc_low && rtc_high-rtc_low>=0x400+sizeof(metalio_early_key_record_t) &&
        desc->address>=rtc_low &&
        desc->address<=rtc_high-0x400-sizeof(metalio_early_key_record_t);
}

static inline uint32_t metalio_early_key_checksum(const metalio_early_key_record_t *record) {
    const uint8_t *bytes=(const uint8_t *)record;
    uint32_t hash=UINT32_C(2166136261);
    for(unsigned i=0;i<28;i++) hash=(hash^bytes[i])*UINT32_C(16777619);
    return hash;
}
typedef bool (*metalio_early_key_read_fn)(uint8_t reg,uint8_t *value);
typedef void (*metalio_early_key_delay_fn)(unsigned us);
static inline metalio_early_key_record_t metalio_early_key_sample(
        unsigned reason,metalio_early_key_read_fn read_reg,metalio_early_key_delay_fn delay) {
    metalio_early_key_record_t record={.magic=METALIO_EARLY_KEY_MAGIC,.version=1,
        .board=METALIO_EARLY_KEY_BOARD,.reason=reason,.samples=0xffff,.config=0xffff};
    uint8_t config=0xff,invert=0xff,first=0xff,second=0xff;
    if(reason==METALIO_EARLY_KEY_POWERON && read_reg(7,&config) && (config&0x80) &&
       read_reg(5,&invert) && !(invert&0x80) && read_reg(1,&first)) {
        delay(30000);
        if(read_reg(1,&second)) {
            record.flags=METALIO_EARLY_KEY_VALID;
            if(!(first&0x80) && !(second&0x80)) record.flags|=METALIO_EARLY_KEY_PRESSED;
        }
    }
    record.samples=(uint32_t)first|((uint32_t)second<<8);
    record.config=(uint32_t)config|((uint32_t)invert<<8);
    record.checksum=metalio_early_key_checksum(&record);
    return record;
}
static inline bool metalio_early_key_take(void *storage,unsigned reason,metalio_early_key_record_t *taken) {
    metalio_early_key_record_t record;
    memcpy(&record,storage,sizeof(record));
    memset(storage,0,sizeof(record));  // consume before any admission, including malformed records
    if(taken) *taken=record;
    return reason==METALIO_EARLY_KEY_POWERON && record.reason==reason &&
        record.magic==METALIO_EARLY_KEY_MAGIC && record.version==1 &&
        record.board==METALIO_EARLY_KEY_BOARD &&
        record.checksum==metalio_early_key_checksum(&record) &&
        record.flags==(METALIO_EARLY_KEY_VALID|METALIO_EARLY_KEY_PRESSED) &&
        record.samples<=0xffff && !(record.samples&0x8080) &&
        record.config<=0xffff && (record.config&0x80) && !(record.config&0x8000);
}

