/* SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
 * 中文：断行和绘制共用的词间空格伸缩预算，单位为像素。
 * English: Shared pixel budgets for word-space stretch and shrink in layout and rendering.
 */
#pragma once
static inline int text_space_stretch(int advance) { return advance > 1 ? advance / 2 : 1; }
static inline int text_space_shrink(int advance) { return advance > 2 ? advance / 3 : 0; }
