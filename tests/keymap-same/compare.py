#!/usr/bin/env python3
"""今の版（reference.keymap）と config/AroundForty-RB.keymap の中身を比べる。違えば exit 1。

比べる物:
- レイヤーの名前と順番、各レイヤーの bindings の並び（キーごと）
- コンボ（名前・bindings・key-positions・layers）
- 各レイヤーの bindings 以外の中身（sensor-bindings など）
- マクロの中身（`<&out OUT_BLE>,` の 1 手は除いて比べる。載せ替えで足した物）
- behaviors の中身（プロパティまで）、conditional_layers、`&mt { … }` のような上書きの塊、#define
意図して変えたキーは allowed.txt に「<レイヤーの名前> <位置>」で 1 行ずつ書く（理由を # の後に）。
意図して変えたマクロは「macro <名前>」、behavior は「behavior <名前>」で書く（中身の比べを外す）。
使い方: compare.py <reference.keymap> <new.keymap> [allowed.txt]
"""
import re
import sys


def strip_comments(t):
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def block(text, name):
    """`name {` から対応する `}` までの中身"""
    m = re.search(r"\b" + re.escape(name) + r"\s*\{", text)
    if not m:
        return None
    i, depth = m.end(), 1
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


def children(body):
    """直下の子ノード: [(名前, 中身)]"""
    out, i = [], 0
    pat = re.compile(r"([A-Za-z0-9_+,\-]+(?:\s*:\s*[A-Za-z0-9_+,\-]+)?)\s*\{")
    while True:
        m = pat.search(body, i)
        if not m:
            return out
        j, depth = m.end(), 1
        while depth:
            depth += body[j] == "{"
            depth -= body[j] == "}"
            j += 1
        name = m.group(1).split(":")[-1].strip()
        out.append((name, body[m.end():j - 1]))
        i = j


def prop(body, key):
    m = re.search(r"\b" + re.escape(key) + r"\s*=\s*(.*?);", body, flags=re.S)
    return " ".join(m.group(1).split()) if m else None


def bindings(body):
    p = prop(body, "bindings")
    if p is None:
        return []
    p = p.replace("<", " ").replace(">", " ").replace(",", " ")
    # 括弧の中の空白でキーが割れないように
    p = re.sub(r"\(\s*", "(", p)
    p = re.sub(r"\s*\)", ")", p)
    keys, cur = [], []
    for tok in p.split():
        if tok.startswith("&") and cur:
            keys.append(" ".join(cur))
            cur = []
        cur.append(tok)
    if cur:
        keys.append(" ".join(cur))
    return keys


def norm(s):
    return " ".join(s.split())


def without_bindings(body):
    """bindings = <…>; を除いた中身（sensor-bindings は残す）"""
    return norm(re.sub(r"(?<![-\w])bindings\s*=.*?;", "", body, flags=re.S))


def overrides(text):
    """ルートの `&name { … }` の塊"""
    out = {}
    for m in re.finditer(r"^&([A-Za-z0-9_]+)\s*\{", text, flags=re.M):
        i, depth = m.end(), 1
        while depth:
            depth += text[i] == "{"
            depth -= text[i] == "}"
            i += 1
        out[m.group(1)] = norm(text[m.end():i - 1])
    return out


def parse(path):
    t = strip_comments(open(path, encoding="utf-8").read())
    keymap = block(t, "keymap")
    layers = [(n, bindings(b)) for n, b in children(keymap)]
    layer_rest = {n: without_bindings(b) for n, b in children(keymap)}
    combos = {n: (prop(b, "bindings"), prop(b, "key-positions"), prop(b, "layers"))
              for n, b in children(block(t, "combos") or "")}
    macros = {n: norm(re.sub(r"<&out OUT_BLE>\s*,", "", b))
              for n, b in children(block(t, "macros") or "")}
    behaviors = {n: norm(b) for n, b in children(block(t, "behaviors") or "")}
    cond = {n: norm(b) for n, b in children(block(t, "conditional_layers") or "")}
    defines = sorted(norm(l) for l in t.splitlines() if l.strip().startswith("#define"))
    return layers, combos, macros, behaviors, layer_rest, cond, overrides(t), defines


def main():
    ref, new = parse(sys.argv[1]), parse(sys.argv[2])
    allowed, allowed_macros, allowed_behaviors = set(), set(), set()
    if len(sys.argv) > 3:
        for line in open(sys.argv[3], encoding="utf-8"):
            line = line.split("#")[0].split()
            if len(line) == 2 and line[0] == "macro":
                allowed_macros.add(line[1])
            elif len(line) == 2 and line[0] == "behavior":
                allowed_behaviors.add(line[1])
            elif len(line) == 2:
                allowed.add((line[0], int(line[1])))
    errs = []
    rl, nl = ref[0], new[0]
    if [n for n, _ in rl] != [n for n, _ in nl]:
        errs.append(f"レイヤーの名前・順番が違う: {[n for n, _ in rl]} → {[n for n, _ in nl]}")
    for (rn, rb), (nn, nb) in zip(rl, nl):
        if len(rb) != len(nb):
            errs.append(f"{rn}: キーの数 {len(rb)} → {len(nb)}")
        for i, (a, b) in enumerate(zip(rb, nb)):
            if a != b and (rn, i) not in allowed:
                errs.append(f"{rn} {i}: {a} → {b}")
    if ref[1] != new[1]:
        for k in sorted(set(ref[1]) | set(new[1])):
            if ref[1].get(k) != new[1].get(k):
                errs.append(f"コンボ {k}: {ref[1].get(k)} → {new[1].get(k)}")
    for k, v in ref[2].items():
        if k not in new[2]:
            errs.append(f"マクロ {k} が無い")
        elif new[2][k] != v and k not in allowed_macros:
            errs.append(f"マクロ {k} の中身が違う")
    for k, v in ref[3].items():
        if k not in new[3]:
            errs.append(f"behavior {k} が無い")
        elif new[3][k] != v and k not in allowed_behaviors:
            errs.append(f"behavior {k} の中身が違う: {v} → {new[3][k]}")
    for k, v in ref[4].items():
        if new[4].get(k, v) != v:
            errs.append(f"レイヤー {k} の bindings 以外が違う: {v} → {new[4][k]}")
    if ref[5] != new[5]:
        errs.append(f"conditional_layers が違う: {ref[5]} → {new[5]}")
    if ref[6] != new[6]:
        errs.append(f"上書きの塊（&mt など）が違う: {ref[6]} → {new[6]}")
    if ref[7] != new[7]:
        errs.append(f"#define が違う: {ref[7]} → {new[7]}")
    print(f"レイヤー {len(rl)} 枚・コンボ {len(ref[1])} 個・マクロ {len(ref[2])} 個・behaviors {len(ref[3])} 個を比べた")
    for e in errs:
        print("違い:", e)
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
