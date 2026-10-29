/* SPDX-FileCopyrightText: 2026 mindreset
 * SPDX-License-Identifier: Apache-2.0
 * Shared image lock menu; storage and presentation remain page/board-owned.
 */
typedef enum {IMAGE_LOCK_ANY, IMAGE_LOCK_WALLPAPER, IMAGE_LOCK_BOOKMARK} image_lock_mode_t;
static image_lock_mode_t s_lock_mode, s_requested_lock_mode;
static bool s_lock_menu;
static unsigned image_lock_action_count(void) { return s_lock_mode==IMAGE_LOCK_ANY?2:1; }
static unsigned image_lock_style(unsigned action) {
    return s_lock_mode==IMAGE_LOCK_BOOKMARK || (s_lock_mode==IMAGE_LOCK_ANY&&action==1)?3:1;
}
// 绘制与命中共用几何；卡片之外保留原图，不额外输出背景帧。
// Share paint/hit geometry; retain the image outside the card without an extra background presentation.
static EpdRect image_lock_option(unsigned index) {
    return (EpdRect){102, 450 + (int)index * 96, 480, 80};
}
static void image_lock_menu_draw(uint8_t *fb) {
    const unsigned actions=image_lock_action_count();
    const EpdRect card = {70, 346, 544, actions==2?468:372};
    if (!ui_glass_panel_frost(fb, card, 28, 96, 3, true))
        ui_fill_round_rect(fb, card, 28, UI_GRAY_WHITE);
    ui_draw_round_rect(fb, card, 28, UI_GRAY_LIGHT);
    ui_draw_icon(fb, 124, 402, 34, UI_ICON_LOCK, 0);
    ui_text_vc(fb, 162, 402, 30, "设为锁屏", EPD_DRAW_ALIGN_LEFT, false);
    const char *labels[] = {"设为壁纸锁屏", "设为透明书封"};
    const ui_icon_t icons[] = {UI_ICON_HOUSE, UI_ICON_BOOKMARK};
    for (unsigned i = 0; i < actions; ++i) {
        unsigned option=image_lock_style(i)==3?1:0;
        EpdRect r = image_lock_option(i);
        ui_fill_round_rect(fb, r, 18, UI_GRAY_WHITE);
        ui_draw_icon(fb, r.x + 36, r.y + 40, 32, icons[option], 0);
        ui_text_vc(fb, r.x + 72, r.y + 40, 27, labels[option], EPD_DRAW_ALIGN_LEFT, false);
        ui_draw_icon(fb, r.x + r.width - 30, r.y + 40, 24, UI_ICON_CHEVRON_RIGHT, 0);
    }
    ui_draw_button(fb, image_lock_option(actions), "取消", false);
    if (s_message[0]) ui_text_vc(fb, 342, card.y+card.height-26, 18, s_message, EPD_DRAW_ALIGN_CENTER, false);
}
