#!/usr/bin/env python3
"""試験用にキーマップを写す。native_sim（BLE なし・外のモジュールなし）で組めない参照だけを置き換える。

- `#include <behaviors/rgbled_widget.dtsi>` を外す（RGB のモジュールは試験に入れない）
- `&bt BT_SEL n` / `&bt BT_CLR` などを `&none` に（BLE なしでは &bt の実体が無い）
使い方: prep_keymap.py <元の .keymap> <写し先>
"""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding="utf-8").read()
text = re.sub(r"^\s*#include\s*<behaviors/rgbled_widget\.dtsi>.*$", "", text, flags=re.M)
text = re.sub(r"&bt\s+BT_[A-Z_]+(\s+\d+)?", "&none", text)
open(dst, "w", encoding="utf-8").write(text)
