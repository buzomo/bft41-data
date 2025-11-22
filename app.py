from flask import Flask, request, jsonify
import os
import uuid
from neon import connect

app = Flask(__name__)


# Neon DB接続設定
def get_db_connection():
    return connect(os.getenv("DATABASE_URL"))


# データ取得エンドポイント
@app.route("/api/data", methods=["GET"])
def get_data():
    token = request.args.get("token")
    if not token:
        return jsonify({"error": "Token is required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT data, (public_token = %s) AS is_readonly
        FROM bft41_data
        WHERE private_token = %s OR public_token = %s
    """,
        (token, token, token),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Token not found"}), 404

    data, is_readonly = row
    return jsonify({"data": data, "isReadOnly": is_readonly})


# データ保存エンドポイント
@app.route("/api/data", methods=["POST"])
def save_data():
    token = request.json.get("token")
    data = request.json.get("data")
    if not token or not data:
        return jsonify({"error": "Token and data are required"}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    # private_tokenでのみ更新可能
    cur.execute(
        """
        UPDATE bft41_data
        SET data = %s
        WHERE private_token = %s
        RETURNING *
    """,
        (data, token),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Invalid token"}), 403

    return jsonify({"success": True})


# 共有トークン生成エンドポイント
@app.route("/api/share", methods=["POST"])
def generate_share_token():
    private_token = request.json.get("privateToken")
    if not private_token:
        return jsonify({"error": "privateToken is required"}), 400

    public_token = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE bft41_data
        SET public_token = %s
        WHERE private_token = %s
    """,
        (public_token, private_token),
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"publicToken": public_token})


# トークン生成エンドポイント（新規ユーザー用）
@app.route("/api/token", methods=["GET"])
def generate_token():
    private_token = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO bft41_data (private_token, data)
        VALUES (%s, '{}')
    """,
        (private_token,),
    )
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"privateToken": private_token})


if __name__ == "__main__":
    app.run(debug=True)
