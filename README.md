# zmk-config-AroundFortyRB

Around Forty RBのファームウェアです。

-------------------------------------------------------------------------
mainブランチで実装済み
-------------------------------------------------------------------------

🟢Zmkfirmware v0.3に対応。（tsunoshuu様、PR感謝します）

🟢PMW3610のドライバを「badjeff/zmk-pmw3610-driver」に変更

🟢ZMK Studioに対応

🟢全角半角の切り替えマクロ：全角半角のトグルが一つのキーで可能

🟡Prospector Scannerの対応はいったん見送っています　/ ※Bluetooth接続が不安定になるため

以下、ご利用ガイドです。

https://note.com/razily/n/n0b3c5ff58d92

-------------------------------------------------------------------------
以下はmainブランチには未実装の開発版（dev-main）のみの機能です
-------------------------------------------------------------------------

🟢Slow Curor layer：カーソル速度を一時的に遅くて精密操作をしやすくします

🟢2種類のScroll Layer：上下左右のスクロールができるレイヤーと、縦限定スクロールができるレイヤーがあります

-------------------------------------------------------------------------
スリープ復帰後に左手側（Peripheral）が再接続しない問題の修正
-------------------------------------------------------------------------

## 症状

キーボードをしばらく操作せずスリープに入った後、操作によりスリープから復帰した際に、左右分割の左側（Peripheral）が認識されず、電源のON/OFFが必要になる。ほぼ必発。

## 原因分析

BLE（Bluetooth Low Energy）の設定に3つの問題が複合し、スリープ復帰後の再接続を不安定にしていました。

### 原因1：BLE 接続インターバルに余裕がなかった

変更前の設定：
```
CONFIG_BT_PERIPHERAL_PREF_MIN_INT=12   # 15ms
CONFIG_BT_PERIPHERAL_PREF_MAX_INT=12   # 15ms（MIN と同じ＝固定値）
```

BLE の接続インターバル（Central と Peripheral が通信する周期）が「最小15ms・最大15ms」の完全固定値でした。
通常動作中はこれで問題ありませんが、スリープから復帰して再接続する際、BLEスタックは接続パラメータを相手とネゴシエーション（交渉）します。
MIN=MAX だとネゴシエーションの余裕が一切なく、タイミングが少しでもずれると接続確立に失敗します。

### 原因2：左手側（Peripheral）のBLE送信パワーが不足していた

変更前の設定（AroundForty-RB_L.conf）：
```
# CONFIG_BT_CTLR_TX_PWR_PLUS_8 の指定なし（デフォルト＝低出力）
```

右手側（Central）には `CONFIG_BT_CTLR_TX_PWR_PLUS_8=y`（最大出力+8dBm）が設定されていましたが、左手側にはありませんでした。
スリープ復帰後、Peripheral はアドバタイズ（自分の存在を電波で広告）を出して Central に発見してもらう必要があります。
送信パワーがデフォルト（低出力）のままだと、この広告電波が Central に十分届かず、再接続できません。

### 原因3：監視タイムアウトが未指定だった

変更前の設定：
```
# CONFIG_BT_PERIPHERAL_PREF_TIMEOUT の指定なし（デフォルト値に依存）
```

BLE 接続には「監視タイムアウト（Supervision Timeout）」というパラメータがあり、「この時間内に相手から応答がなければ接続切断とみなす」という閾値です。
明示的に指定しない場合、デフォルト値が使われますが、スリープ復帰の再接続プロセスには短すぎる場合があります。

## 修正内容

### AroundForty-RB_L.conf（左手側・Peripheral）— 主な修正

| 設定項目 | 変更前 | 変更後 | 説明 |
|---|---|---|---|
| `CONFIG_BT_PERIPHERAL_PREF_MAX_INT` | `12`（15ms固定） | `24`（30ms） | 接続インターバル上限を広げ、再接続時のネゴシエーションに余裕を持たせる |
| `CONFIG_BT_PERIPHERAL_PREF_TIMEOUT` | 未指定 | `600`（6秒） | 監視タイムアウトを明示的に6秒に設定し、再接続に十分な時間を確保 |
| `CONFIG_BT_CTLR_TX_PWR_PLUS_8` | 未指定 | `y` | BLE送信パワーを最大（+8dBm）にし、スリープ復帰後のアドバタイズ到達距離を確保 |

### AroundForty-RB_R.conf（右手側・Central）— 補助的修正

| 設定項目 | 変更前 | 変更後 | 説明 |
|---|---|---|---|
| `CONFIG_BT_PERIPHERAL_PREF_MAX_INT` | `12`（15ms固定） | `24`（30ms） | ホストPC向けBLE接続でも同様にインターバルに幅を持たせる |
| `CONFIG_BT_PERIPHERAL_PREF_TIMEOUT` | 未指定 | `600`（6秒） | 監視タイムアウトを明示的に設定 |

## 技術的背景

### ZMK のスリープ動作

1. `CONFIG_ZMK_IDLE_TIMEOUT=30000`（30秒）経過すると **アイドル状態** に移行
2. `CONFIG_ZMK_IDLE_SLEEP_TIMEOUT=1800000`（30分）経過すると **ディープスリープ** に移行（`sys_poweroff()`）
3. スリープ中はBLE接続が完全に切断される
4. キー押下で復帰した後、Peripheral がアドバタイズを開始し、Central がスキャンして再接続する

### 再接続が失敗するメカニズム

```
[スリープ復帰]
    ↓
[左手(Peripheral): アドバタイズ開始]  ←── TX パワー不足で電波が届きにくい（原因2）
    ↓
[右手(Central): スキャン → 接続要求]
    ↓
[接続パラメータのネゴシエーション]  ←── MIN=MAX=12 で余裕ゼロ（原因1）
    ↓                                    タイムアウト不明確（原因3）
[失敗 → 接続確立できず]
```

### 関連する ZMK/Zephyr の既知問題

- [zmkfirmware/zmk#718](https://github.com/zmkfirmware/zmk/issues/718) — Peripheral が切断後に自動再接続しない
- [zmkfirmware/zmk#2904](https://github.com/zmkfirmware/zmk/issues/2904) — Peripheral のスリープが Central をハングさせる
- [zmkfirmware/zmk#2408](https://github.com/zmkfirmware/zmk/issues/2408) — Central/Peripheral 間のスリープ同期の要望

## 注意事項

- この修正はフォーク元（razilyis/zmk-config-AroundFortyRB）にも同じ問題が存在します
- 修正後はファームウェアを左右両方に書き込む必要があります
- 初回の書き込み後、BT接続情報のリセット（settings_reset ファームウェアの書き込み）を推奨します
