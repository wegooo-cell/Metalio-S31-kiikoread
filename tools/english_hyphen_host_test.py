#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Kiikoread-Personal-Study-1.0
"""中文：用独立逐模式参考实现核对只读Trie，覆盖例外、大小写及内存边界。
English: Check the read-only trie against an independent pattern-by-pattern oracle, exceptions, case and bounds.
"""
import random
import re
import subprocess
import tempfile
from pathlib import Path
from gen_english_hyphen import ROOT, source_patterns

patterns, exceptions, _ = source_patterns()
parsed = []
for p in patterns:
    letters = re.sub('[0-9]', '', p)
    weights = [0]
    for c in p:
        if c.isdigit(): weights[-1] = int(c)
        else: weights.append(0)
    parsed.append((letters, weights))
exception_map = {}
for e in exceptions:
    word = e.replace('-', '')
    cuts = []
    n = 0
    for c in e:
        if c == '-': cuts.append(n)
        else: n += 1
    exception_map[word] = cuts

def oracle(word):
    if not 5 <= len(word) <= 63 or not re.fullmatch('[a-zA-Z]+', word) or word.isupper(): return []
    word = word.lower()
    if word in exception_map: return [n for n in exception_map[word] if 2 <= n <= len(word)-3]
    text = '.' + word + '.'
    weights = [0] * (len(text) + 1)
    for letters, values in parsed:
        at = text.find(letters)
        while at >= 0:
            for i, v in enumerate(values): weights[at+i] = max(weights[at+i], v)
            at = text.find(letters, at+1)
    return [n for n in range(2, len(word)-2) if weights[n+1] % 2]

words = ['extraordinary','representation','hyphenation','international','algorithm',
         'readers','reader','exception','demonstration','computer','beautiful','Typography',
         'NASA','UTF16',"reader's",'résumé','a'*63,'a'*64,'a'*1000,'abcdefghmnop']
words += list(exception_map)
rng = random.Random(315)
words += [letters.strip('.') for letters, _ in rng.sample(parsed, 650)]
words += [''.join(rng.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(rng.randint(5,63))) for _ in range(350)]
words += ['prefix'+word+'suffix' for word in words[:60]]
unit = r'''
#include "english_hyphen.h"
#include <stdio.h>
#include <assert.h>
int main(void) {
    _Static_assert(sizeof(english_hyphen_node_t)==6,"compact trie");
    char word[2048];
    while(fgets(word,sizeof(word),stdin)) {
        word[strcspn(word,"\n")]=0;
        uint8_t points[64];
        bool valid=english_hyphen_points(word,strlen(word),points);
        for(unsigned i=0;i<64;++i) if(points[i]) {assert(valid&&i>=2&&i+3<=strlen(word));printf("%u,",i);}
        puts("");
    }
    return 0;
}
'''
with tempfile.TemporaryDirectory() as folder:
    work=Path(folder);(work/'test.c').write_text(unit)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined','-I'+str(ROOT/'main/book'),str(work/'test.c'),'-o',str(work/'test')],check=True)
    output=subprocess.run([str(work/'test')],input='\n'.join(words)+'\n',text=True,capture_output=True,check=True).stdout.splitlines()
    assert len(output)==len(words)
    for word, line in zip(words, output):
        actual=[int(n) for n in line.split(',') if n]
        assert actual==oracle(word),(word,actual,oracle(word))
for word in words[:12]: print(word, oracle(word))
print(f'PASS: {len(words)} independent Liang oracle cases, TeX exceptions/minima, rejection and ASan bounds')
