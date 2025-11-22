from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

app = Flask(__name__)
CORS(app)  # CORSを許可

# Neon DB接続設定
def get_db_connection():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), sslmode='require')
    return conn

# データ取得エンドポイント
@app.route('/api/data', methods=['GET'])
def get_data():
    token = request.args.get('token')
    if not token:
        return jsonify({"error": "Token is required"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT data, (public_token = %s) AS is_readonly
                FROM bft41_data
                WHERE private_token = %s OR public_token = %s
            """, (token, token, token))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Token not found"}), 404
            return jsonify({"data": row["data"], "isReadOnly": row["is_readonly"]})
    finally:
        conn.close()

# データ保存エンドポイント
@app.route('/api/data', methods=['POST'])
def save_data():
    token = request.json.get('token')
    data = request.json.get('data')
    if not token or not data:
        return jsonify({"error": "Token and data are required"}), 400

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # private_tokenでのみ更新可能
            cur.execute("""
                UPDATE bft41_data
                SET data = %s
                WHERE private_token = %s
                RETURNING *
            """, (data, token))
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Invalid token"}), 403
            conn.commit()
            return jsonify({"success": True})
    finally:
        conn.close()

# 共有トークン生成エンドポイント
@app.route('/api/share', methods=['POST'])
def generate_share_token():
    private_token = request.json.get('privateToken')
    if not private_token:
        return jsonify({"error": "privateToken is required"}), 400

    public_token = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE bft41_data
                SET public_token = %s
                WHERE private_token = %s
            """, (public_token, private_token))
            conn.commit()
            return jsonify({"publicToken": public_token})
    finally:
        conn.close()

# トークン生成エンドポイント（新規ユーザー用）
@app.route('/api/token', methods=['GET'])
def generate_token():
    private_token = str(uuid.uuid4())
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bft41_data (private_token, data)
                VALUES (%s, '{}')
            """, (private_token,))
            conn.commit()
            return jsonify({"privateToken": private_token})
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
