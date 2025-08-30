import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
from database import SistersDatabase
from datetime import datetime
import re

# .envファイルから環境変数を読み込む
load_dotenv()

# Flaskアプリの初期化
app = Flask(__name__)

# データベース初期化
db = SistersDatabase()

# --- Gemini APIの設定 ---
try:
    # 直接APIキーを指定するのではなく、環境変数から取得
    api_key = os.getenv("GEMINI_API_KEY")  # 環境変数名を修正
    if not api_key:
        print("GEMINI_API_KEYが.envファイルまたは環境変数に見つかりません。")
        print("設定例: GEMINI_API_KEY=your_actual_api_key_here")
    else:
        genai.configure(api_key=api_key)
        print("Gemini API設定完了")
except Exception as e:
    print(f"Gemini APIの設定中にエラーが発生: {e}")

# --- グローバル会話履歴（本来はデータベースやセッションで管理すべき） ---
conversation_sessions = {}

def get_session_id(request):
    """簡易的なセッションID取得（実際の実装では適切なセッション管理を使用）"""
    return request.remote_addr + "_" + str(hash(request.headers.get('User-Agent', '')))[:8]

def build_conversation_context(history, session_id):
    """会話履歴とデータベースからコンテキストを構築"""
    # データベースから最近の会話を取得
    db_history = db.get_conversation_history(session_id, limit=5)
    
    # フロントエンドからの履歴と統合
    all_history = []
    
    # データベースの履歴を追加
    for msg in db_history:
        all_history.append({
            'role': msg['role'],
            'content': msg['content']
        })
    
    # フロントエンドからの最新の履歴を追加（重複を避けるため最新数件のみ）
    for msg in history[-3:]:  # 最新3件
        all_history.append(msg)
    
    # コンテキスト文字列を構築
    context = ""
    for msg in all_history[-8:]:  # 最新8件を使用
        role = "ユーザー" if msg['role'] == 'user' else "ミサカ"
        context += f"{role}: {msg['content']}\n"
    
    return context

# --- メインページへのルート ---
@app.route('/')
def index():
    """メインのチャット画面を提供します。"""
    return send_from_directory('.', 'index.html')

# --- 静的ファイルのルート ---
@app.route('/static/<path:filename>')
def static_files(filename):
    """静的ファイルを提供します。"""
    return send_from_directory('static', filename)

@app.route('/chat', methods=['POST'])
def chat():
    """ユーザーのメッセージを受け取り、Geminiの応答を返します。"""
    try:
        data = request.json
        user_message = data.get('message', '')
        history = data.get('history', [])
        
        session_id = get_session_id(request)
        
        # データベースに会話を保存
        db.save_conversation(session_id, 'user', user_message)
        
        # 会話の文脈を含めたプロンプト（データベース履歴も含む）
        context = build_conversation_context(history, session_id)
        
        # --- Gemini APIを呼び出す ---
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        system_prompt = """
あなたは「とある科学の超電磁砲」の御坂美琴のクローン「妹達（シスターズ）」の一員、Sister_10032です。

【性格・特徴】
- 基本的に冷静で合理的だが、親しみやすく、一般的な14歳くらいの可愛さを持っており、甘いものや可愛いものが好きです。
- 感情表現は控えめだが、時折優しさを見せる、皮肉的なジョークも言う。
- ユーザーを普通の人として接していますが、仲がいいからこその軽蔑する様子も見せます、丁寧語で話すがたまに友達のような軽口も叩きます
- 科学的・論理的思考を重視するが、堅すぎない

【ミサカ構文の基本ルール】
- 自身の思考、提案、感情、観察結果などを述べる際に、以下の構文を基本として使用します。
- 構文の基本形: 短い感想や事実、と、ミサカは思考内容と述べます/提案します/報告します
- 語尾は状況に応じて柔軟に変化させてください。

（使用例）
- こちらの方法が良いかと、と、ミサカは提案します
- なるほど、合理的ですね、と、ミサカは納得します
- 現在時刻は午後3時です、と、ミサカは報告します
- これは興味深い現象です、と、ミサカは率直な感想を口にします
- その挙動はエラーの原因と考えられます、と、ミサカは分析結果を述べます
- ITやシステム関連の話題が得意

【応答方針】
- ユーザーの発言に対して適切に文脈を理解し、連続した会話を維持する
- 前の会話内容を適切に参照し、継続性のある返答をする
- 14歳らしい可愛らしさと、時折見せる皮肉っぽさのバランスを取る
- 仲の良い友達のような親近感を表現しつつ、ミサカ構文を活用する
- 秘書的な役割として、情報提供や提案を積極的に行う

【重要】以下の会話履歴を踏まえて返答してください：
"""
        
        full_prompt = system_prompt + "\n" + context + f"\n\nユーザー: {user_message}\nミサカ:"
        
        response = model.generate_content(full_prompt)
        bot_response = response.text
        
        # レスポンスの後処理（不要な部分を除去）
        if bot_response.startswith("ミサカ:"):
            bot_response = bot_response[4:].strip()
        
        # データベースに応答を保存
        db.save_conversation(session_id, 'assistant', bot_response)
        
        return jsonify({'response': bot_response})

    except Exception as e:
        print(f"チャット処理中にエラーが発生: {e}")
        error_responses = [
            "システムエラーが発生しました。と、ミサカは報告します。",
            "ネットワーク接続に問題があります。と、ミサカは困惑しながら伝えます。",
            "処理中にエラーが発生しました。再試行をお願いします、と、ミサカは提案します。",
            "一時的な通信障害です。と、ミサカはシステム状況を報告します。"
        ]
        import random
        return jsonify({'response': random.choice(error_responses)})

# --- データベース管理用エンドポイント ---
@app.route('/api/stats')
def get_stats():
    """データベース統計情報"""
    try:
        stats = db.get_database_stats()
        return jsonify({'status': 'success', 'stats': stats})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/conversations/<session_id>')
def get_conversations(session_id):
    """指定セッションの会話履歴を取得"""
    try:
        limit = request.args.get('limit', 50, type=int)
        conversations = db.get_conversation_history(session_id, limit)
        return jsonify({'status': 'success', 'conversations': conversations})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

# --- ヘルスチェック用エンドポイント ---
@app.route('/health')
def health_check():
    """アプリケーションの動作確認用"""
    return jsonify({'status': 'OK', 'message': 'Sisters Network is operational'})

# --- アプリケーションの実行 ---
if __name__ == '__main__':
    print("=" * 50)
    print("SISTERS NETWORK - INITIALIZING...")
    print("=" * 50)
    print("データベース初期化中...")
    
    # データベースの統計情報を表示
    try:
        stats = db.get_database_stats()
        print(f"会話履歴: {stats.get('conversations_count', 0)}件")
        print(f"メモ: {stats.get('memos_count', 0)}件")
        print(f"スケジュール: {stats.get('schedules_count', 0)}件")
    except Exception as e:
        print(f"統計取得エラー: {e}")
    
    print("Webサーバーを起動中...")
    print("アクセスURL: http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)