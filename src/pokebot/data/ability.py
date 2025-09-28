from pokebot.core.events import Event, Handler
from .registry import AbilityData
from pokebot.handlers.ability import after_stat_change, on_switch_in

ABILITIES: dict[str, AbilityData] = {
    "": AbilityData(name=""),
    "ARシステム": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    },
    "あくしゅう": {},
    "あついしぼう": {},
    "あとだし": {},
    "あまのじゃく": {},
    "あめうけざら": {},
    "あめふらし": {},
    "ありじごく": {},
    "いかく": AbilityData(
        name="いかく",
        handlers={Event.ON_SWITCH_IN: Handler(on_switch_in.いかく, 4, True)}
    ),
    "いかりのこうら": {},
    "いかりのつぼ": {
        "flags": [
            "undeniable"
        ]
    },
    "いしあたま": {},
    "いたずらごころ": {},
    "いやしのこころ": {},
    "いろめがね": {},
    "いわはこび": {},
    "うのミサイル": {
        "flags": [
            "unreproducible",
            "protected",
            "undeniable"
        ]
    },
    "うるおいボイス": {},
    "うるおいボディ": {},
    "えんかく": {},
    "おうごんのからだ": {},
    "おどりこ": {
        "flags": [
            "undeniable"
        ]
    },
    "おみとおし": {},
    "おもてなし": {},
    "おやこあい": {},
    "おわりのだいち": {
        "flags": [
            "undeniable"
        ]
    },
    "かいりきバサミ": {},
    "かがくへんかガス": {
        "flags": [
            "unreproducible"
        ]
    },
    "かげふみ": {},
    "かぜのり": {},
    "かそく": {},
    "かたいツメ": {},
    "かたやぶり": {},
    "かちき": AbilityData(
        name="かちき",
        flags=["undeniable"],
        handlers={Event.ON_MODIFY_RANK: Handler(after_stat_change.かちき, 0)}
    ),
    "かるわざ": {},
    "かわりもの": {
        "flags": [
            "unreproducible"
        ]
    },
    "かんそうはだ": {},
    "かんろなミツ": {
        "flags": [
            "one_time"
        ]
    },
    "がんじょう": {},
    "がんじょうあご": {},
    "ききかいひ": {
        "flags": [
            "undeniable"
        ]
    },
    "きけんよち": {},
    "きみょうなくすり": {},
    "きもったま": {},
    "きゅうばん": {},
    "きょううん": {},
    "きょうえん": {},
    "きょうせい": {},
    "きよめのしお": {},
    "きれあじ": {},
    "きんしのちから": {},
    "きんちょうかん": AbilityData(
        name="きんちょうかん",
        handlers={Event.ON_SWITCH_IN: Handler(on_switch_in.きんちょうかん, 3)}
    ),
    "ぎたい": {
        "flags": [
            "undeniable"
        ]
    },
    "ぎゃくじょう": {
        "flags": [
            "undeniable"
        ]
    },
    "ぎょぐん": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    },
    "くいしんぼう": {},
    "くさのけがわ": {},
    "くだけるよろい": {
        "flags": [
            "undeniable"
        ]
    },
    "くろのいななき": {},
    "げきりゅう": {},
    "こおりのりんぷん": {},
    "こだいかっせい": {
        "flags": [
            "unreproducible",
            "undeniable"
        ]
    },
    "こぼれダネ": {
        "flags": [
            "undeniable"
        ]
    },
    "こんがりボディ": {},
    "こんじょう": {},
    "ごりむちゅう": {},
    "さいせいりょく": {},
    "さまようたましい": {
        "flags": [
            "undeniable"
        ]
    },
    "さめはだ": {
        "flags": [
            "undeniable"
        ]
    },
    "しぜんかいふく": {},
    "しめりけ": {},
    "しゅうかく": {},
    "しょうりのほし": {
        "flags": [
            "undeniable"
        ]
    },
    "しれいとう": {
        "flags": [
            "unreproducible"
        ]
    },
    "しろいけむり": {},
    "しろのいななき": {},
    "しんがん": {},
    "しんりょく": {},
    "じきゅうりょく": {
        "flags": [
            "undeniable"
        ]
    },
    "じしんかじょう": {},
    "じゅうなん": {},
    "じゅくせい": {
        "flags": [
            "undeniable"
        ]
    },
    "じょうききかん": {
        "flags": [
            "undeniable"
        ]
    },
    "じょおうのいげん": {},
    "じりょく": {},
    "じんばいったい": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    },
    "すいすい": {},
    "すいほう": {},
    "すじがねいり": {},
    "すてみ": {},
    "すなおこし": {},
    "すなかき": {},
    "すながくれ": {},
    "すなのちから": {},
    "すなはき": {
        "flags": [
            "undeniable"
        ]
    },
    "すりぬけ": {},
    "するどいめ": {},
    "せいぎのこころ": {
        "flags": [
            "undeniable"
        ]
    },
    "せいしんりょく": {},
    "せいでんき": {},
    "ぜったいねむり": {
        "flags": [
            "unreproducible",
            "protected",
            "undeniable"
        ]
    },
    "そうしょく": {},
    "そうだいしょう": {},
    "たいねつ": {},
    "たまひろい": {},
    "たんじゅん": {},
    "だっぴ": {},
    "ちからずく": {},
    "ちからもち": {},
    "ちくでん": {},
    "ちどりあし": {},
    "ちょすい": {},
    "てきおうりょく": {},
    "てつのこぶし": {},
    "てつのトゲ": {
        "flags": [
            "undeniable"
        ]
    },
    "てんきや": {
        "flags": [
            "unreproducible"
        ]
    },
    "てんねん": {},
    "てんのめぐみ": {},
    "でんきにかえる": {
        "flags": [
            "undeniable"
        ]
    },
    "でんきエンジン": {},
    "とうそうしん": {},
    "とびだすなかみ": {
        "flags": [
            "undeniable"
        ]
    },
    "とれないにおい": {
        "flags": [
            "undeniable"
        ]
    },
    "どくくぐつ": {
        "flags": [
            "unreproducible"
        ]
    },
    "どくげしょう": {
        "flags": [
            "undeniable"
        ]
    },
    "どくしゅ": {},
    "どくのくさり": {},
    "どくのトゲ": {
        "flags": [
            "undeniable"
        ]
    },
    "どくぼうそう": {},
    "どしょく": {},
    "どんかん": {},
    "なまけ": {},
    "にげあし": {},
    "にげごし": {
        "flags": [
            "undeniable"
        ]
    },
    "ぬめぬめ": {
        "flags": [
            "undeniable"
        ]
    },
    "ねつこうかん": {},
    "ねつぼうそう": {},
    "ねんちゃく": {},
    "のろわれボディ": {
        "flags": [
            "undeniable"
        ]
    },
    "はがねつかい": {},
    "はがねのせいしん": {},
    "はじまりのうみ": {
        "flags": [
            "undeniable"
        ]
    },
    "はっこう": {},
    "はとむね": {},
    "はやあし": {},
    "はやおき": {},
    "はやてのつばさ": {},
    "はらぺこスイッチ": {
        "flags": [
            "unreproducible"
        ]
    },
    "はりきり": {},
    "はりこみ": {},
    "はんすう": {
        "flags": [
            "undeniable"
        ]
    },
    "ばけのかわ": {
        "flags": [
            "unreproducible",
            "protected",
            "one_time"
        ]
    },
    "ばんけん": {},
    "ひでり": {},
    "ひとでなし": {},
    "ひひいろのこどう": {},
    "ひらいしん": {},
    "びびり": {
        "flags": [
            "undeniable"
        ]
    },
    "びんじょう": {
        "flags": [
            "undeniable"
        ]
    },
    "ふうりょくでんき": {
        "flags": [
            "undeniable"
        ]
    },
    "ふかしのこぶし": {},
    "ふくがん": {},
    "ふくつのこころ": {},
    "ふくつのたて": {
        "flags": [
            "one_time"
        ]
    },
    "ふしぎなうろこ": {},
    "ふしぎなまもり": {},
    "ふしょく": {},
    "ふとうのけん": {
        "flags": [
            "one_time"
        ]
    },
    "ふみん": {},
    "ふゆう": {},
    "ぶきよう": {},
    "へんげんじざい": {},
    "へんしょく": {
        "flags": [
            "undeniable"
        ]
    },
    "ほうし": {
        "flags": [
            "undeniable"
        ]
    },
    "ほおぶくろ": {},
    "ほのおのからだ": {
        "flags": [
            "undeniable"
        ]
    },
    "ほろびのボディ": {
        "flags": [
            "undeniable"
        ]
    },
    "ぼうおん": {},
    "ぼうじん": {},
    "ぼうだん": {},
    "まけんき": {
        "flags": [
            "undeniable"
        ]
    },
    "みずがため": {
        "flags": [
            "undeniable"
        ]
    },
    "みずのベール": {},
    "みつあつめ": {},
    "むしのしらせ": {},
    "めんえき": {},
    "もうか": {},
    "ものひろい": {},
    "もふもふ": {},
    "もらいび": {},
    "やるき": {},
    "ゆうばく": {
        "flags": [
            "undeniable"
        ]
    },
    "ゆきかき": {},
    "ゆきがくれ": {},
    "ゆきふらし": {},
    "ようりょくそ": {},
    "よちむ": {},
    "よびみず": {},
    "よわき": {},
    "りゅうのあぎと": {},
    "りんぷん": {},
    "わざわいのうつわ": {
        "flags": [
            "undeniable"
        ]
    },
    "わざわいのおふだ": {
        "flags": [
            "undeniable"
        ]
    },
    "わざわいのたま": {
        "flags": [
            "undeniable"
        ]
    },
    "わざわいのつるぎ": {},
    "わたげ": {
        "flags": [
            "undeniable"
        ]
    },
    "わるいてぐせ": {
        "flags": [
            "undeniable"
        ]
    },
    "アイスフェイス": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    },
    "アイスボディ": {},
    "アナライズ": {},
    "アロマベール": {},
    "イリュージョン": {
        "flags": [
            "unreproducible"
        ]
    },
    "エアロック": {
        "flags": [
            "undeniable"
        ]
    },
    "エレキメイカー": {},
    "オーラブレイク": {},
    "カブトアーマー": {},
    "カーリーヘアー": {
        "flags": [
            "undeniable"
        ]
    },
    "クイックドロウ": {},
    "クォークチャージ": {
        "flags": [
            "unreproducible",
            "undeniable"
        ]
    },
    "クリアボディ": {},
    "グラスメイカー": {},
    "サイコメイカー": {},
    "サンパワー": {},
    "サーフテール": {},
    "シェルアーマー": {},
    "シンクロ": {
        "flags": [
            "undeniable"
        ]
    },
    "スイートベール": {},
    "スカイスキン": {},
    "スキルリンク": {},
    "スクリューおびれ": {},
    "スナイパー": {},
    "スロースタート": {},
    "スワームチェンジ": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    },
    "ゼロフォーミング": {
        "flags": [
            "unreproducible"
        ]
    },
    "ソウルハート": {},
    "ターボブレイズ": {},
    "ダウンロード": {},
    "ダルマモード": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    },
    "ダークオーラ": {
        "flags": [
            "undeniable"
        ]
    },
    "テイルアーマー": {},
    "テクニシャン": {},
    "テラスシェル": {
        "flags": [
            "unreproducible"
        ]
    },
    "テラスチェンジ": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    },
    "テラボルテージ": {},
    "テレパシー": {},
    "デルタストリーム": {
        "flags": [
            "undeniable"
        ]
    },
    "トランジスタ": {},
    "トレース": {
        "flags": [
            "unreproducible"
        ]
    },
    "ナイトメア": {},
    "ノーてんき": {
        "flags": [
            "undeniable"
        ]
    },
    "ノーガード": {
        "flags": [
            "undeniable"
        ]
    },
    "ノーマルスキン": {},
    "ハドロンエンジン": {},
    "ハードロック": {},
    "バッテリー": {
        "flags": [
            "undeniable"
        ]
    },
    "バトルスイッチ": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    },
    "バリアフリー": {},
    "パステルベール": {},
    "パワースポット": {
        "flags": [
            "undeniable"
        ]
    },
    "パンクロック": {},
    "ヒーリングシフト": {},
    "ビビッドボディ": {},
    "ビーストブースト": {},
    "ファントムガード": {
        "flags": [
            "undeniable"
        ]
    },
    "ファーコート": {},
    "フィルター": {},
    "フェアリーオーラ": {
        "flags": [
            "undeniable"
        ]
    },
    "フェアリースキン": {},
    "フラワーギフト": {
        "flags": [
            "unreproducible"
        ]
    },
    "フラワーベール": {},
    "フリーズスキン": {},
    "フレンドガード": {},
    "ブレインフォース": {},
    "プラス": {},
    "プリズムアーマー": {
        "flags": [
            "undeniable"
        ]
    },
    "プレッシャー": {
        "flags": [
            "undeniable"
        ]
    },
    "ヘドロえき": {
        "flags": [
            "undeniable"
        ]
    },
    "ヘヴィメタル": {},
    "ポイズンヒール": {},
    "マイティチェンジ": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    },
    "マイナス": {},
    "マイペース": {},
    "マグマのよろい": {},
    "マジシャン": {},
    "マジックガード": {
        "flags": [
            "undeniable"
        ]
    },
    "マジックミラー": {},
    "マルチスケイル": {},
    "マルチタイプ": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    },
    "ミイラ": {
        "flags": [
            "undeniable"
        ]
    },
    "ミストメイカー": {},
    "ミラクルスキン": {},
    "ミラーアーマー": {},
    "ムラっけ": {},
    "メガランチャー": {},
    "メタルプロテクト": {
        "flags": [
            "undeniable"
        ]
    },
    "メロメロボディ": {
        "flags": [
            "undeniable"
        ]
    },
    "ヨガパワー": {},
    "ライトメタル": {},
    "リベロ": {},
    "リミットシールド": {
        "flags": [
            "unreproducible",
            "protected",
            "undeniable"
        ]
    },
    "リーフガード": {},
    "レシーバー": {
        "flags": [
            "unreproducible"
        ]
    },
    "ＡＲシステム": {},
    "おもかげやどし": {
        "flags": [
            "unreproducible",
            "protected"
        ]
    }
}
