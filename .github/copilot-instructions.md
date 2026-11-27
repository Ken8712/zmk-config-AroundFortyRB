# Copilot への指示書（zmk-config-AroundFortyRB）

このリポジトリは左右分割のキーボード AroundForty RB（Seeed XIAO nRF52840 ×2、右にトラックボール PMW3610）の ZMK の設定です。
持ち主はけんさん。Issue は窓口の Claude が書き、Copilot が PR を作ります。PR の説明・コメントは日本語で書いてください。

## 版と土台
- ZMK: `config/west.yml` で commit `6e2ef41e022d555b10f116e395832913f71717b3` に固定（Zephyr 4.1）。勝手に上げない
- 外のモジュール: `badjeff/zmk-pmw3610-driver`（`44b4a76b`）・`caksoylar/zmk-rgbled-widget`（`e6b46779`）。どちらも commit 固定
- ボード: `xiao_ble//zmk`（旧名 `seeeduino_xiao_ble` は使わない）
- PMW3610 の Kconfig は `CONFIG_PMW3610_ALT_*`、compatible は `pixart,pmw3610-alt`（Zephyr 4.1 の本体のドライバと名前を分けたため）
- NFC のピンは devicetree の `&uicr { nfct-pins-as-gpios; }`（`CONFIG_NFCT_PINS_AS_GPIOS` は無い）

## ビルド（`build.yaml` の 3 行。変えない）
| board | shield | snippet |
|---|---|---|
| `xiao_ble//zmk` | `AroundForty-RB_R rgbled_adapter` | `studio-rpc-usb-uart` |
| `xiao_ble//zmk` | `AroundForty-RB_L rgbled_adapter` | |
| `xiao_ble//zmk` | `settings_reset` | |

- 右（R）が central（端末と繋がる側）、左（L）が peripheral
- workflow `build` が 3 つとも通ることが PR の最低条件

## 試験
- workflow `test`（`.github/workflows/test.yml`）が `tests/*` を ZMK の `app/tests/aroundforty/` に写し、`native_sim` で `./run-test.sh tests/aroundforty` を回す
- 試験 1 件は `tests/<名前>/{native_sim.keymap,events.patterns,keycode_events.snapshot}`。キーの押し離しは `ZMK_MOCK_PRESS(行,列,ms)`／`ZMK_MOCK_RELEASE`
- snapshot は手で書く（`ZMK_TESTS_AUTO_ACCEPT` で出た物をそのまま期待にしない）
- workflow `test` の `keymap-same` は `tests/keymap-same/compare.py` で、今の版（`reference.keymap`）と比べてレイヤー・キー・コンボ・マクロ・behaviors のプロパティ・conditional_layers・`&mt { … }` の上書き・#define が欠けたり変わったりしていないかを見る（マクロの頭の `<&out OUT_BLE>,` は除いて比べる）。意図して変えたキーは `tests/keymap-same/allowed.txt` に「<レイヤーの名前> <位置>  # 理由」、マクロは「macro <名前>  # 理由」、behavior は「behavior <ノードの名前>  # 理由」で足す（それ以外の違いは落ちる）
- 試験のキーマップは `tests/prep_keymap.py` が `config/AroundForty-RB.keymap` を写した物（RGB の include を外し、`&bt …` を `&none` に）。試験の `&kscan` は `rows = <1>; columns = <42>;` で、位置＝キーマップの並びの番号（0 から）
- キーマップを変える Issue では、その変更を確かめる試験を 1 件足す

## 触らない所
- `build.yaml` の `settings_reset` の行と、右の `snippet: studio-rpc-usb-uart`
- `config/west.yml` の commit（Issue に書いてあるときだけ変える）
- `zephyr/module.yml`（あれば）
- `Data/` の下（ケース・画像）
- Kconfig で「見えない」シンボル（prompt の無い物）に値を書いても黙って捨てられる。`BT_HCI_TX_STACK_SIZE` のように `_WITH_PROMPT` が要る物がある。BLE の値を足したら、ビルドの `build/zephyr/.config` に書いた値がそのまま出ているかを PR の説明に書く

## キーの呼び方（けんさんとの言葉。PR の説明はこれで書く）
- 親指のキー: 左が `L1`〜`L3`、右が `R1`・`R2`（左からの順。2 が左右ともホームの位置）
  | 呼び方 | 今のキー（タップ／ホールド） |
  |---|---|
  | L1 | 英数（LANG2）／iPad へ切り替え＋レイヤー 6 |
  | L2 | Space／レイヤー 4 |
  | L3 | かな（LANG1）／レイヤー 9 |
  | R1 | Backspace |
  | R2 | Enter／レイヤー 2 |
- 下段の親指以外: 左から `FnL1`〜`FnL3`（今は Ctrl・Win・Alt）、右の `FnR1`・`FnR2`（今は PgUp・PgDn）
- 下から 2 段目のいちばん中央寄り: 左 `LM`、右 `RM`
- そのほかのキー: Windows のレイヤー（1 番）で出す文字で呼ぶ（「Q のキー」「-（マイナス）のキー」）
- レイヤーは名前で呼ぶ（iPad＝0・Windows＝1・数字記号・マウス・スクロール…）。番号は括弧で添えるだけ
- 押し方: 押す（タップ）／押したまま（ホールド）／2 つ同時（コンボ）

## キーマップの約束
- 電源を入れた直後のレイヤーは iPad（0 番）
- iPad と Windows の切り替えは `tog_on`／`tog_off` と BT の切り替えのマクロ（`bt0`・`bt2`・`bt3`）で行う。この作りを壊さない
- 出力は Bluetooth が既定。USB を挿しても勝手に USB に移らないこと
