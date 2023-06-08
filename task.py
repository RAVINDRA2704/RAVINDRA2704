from flask import Flask, request, jsonify, g, abort
import sqlite3

app = Flask(__name__)


class CreateTables:

    def __init__(self):
        conn = sqlite3.connect('task.db')
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS post (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            user_id INTEGER,
            private INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS like (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_id INTEGER, 
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES post(id) ON DELETE CASCADE,    
            FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
        )
        ''')

        conn.commit()
        cursor.close()


CreateTables()


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect('task.db')
    return db


@app.route('/api/user', methods=['POST'])
def add_user():
    data = request.get_json()
    username = data['username']
    email = data['email']
    password = data['password']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user (username, email, password) VALUES (?, ?, ?)", (username, email, password))
    user_id = cursor.lastrowid

    conn.commit()
    cursor.close()

    return jsonify({'user_id': user_id}), 201


@app.route('/api/user/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_json()
    username = data['username']
    email = data['email']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE user SET username=?, email=? WHERE id=?", (username, email, user_id))

    conn.commit()
    cursor.close()

    return jsonify({'message': 'User updated successfully'}), 200


@app.route('/api/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user.id, user.username, user.email, user.created_at, COUNT(post.id) as num_posts
        FROM user
        LEFT JOIN post ON user.id = post.user_id
        WHERE user.id = ?
        GROUP BY user.id
        ''', (user_id,))
    user = cursor.fetchone()
    cursor.close()

    if user:
        user_data = {
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'created_at': user[3],
            'num_posts': user[4]
        }
        return jsonify(user_data), 200
    else:
        return jsonify({'message': 'User not found'}), 404


@app.route('/api/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user WHERE id=?", (user_id,))

    conn.commit()
    cursor.close()

    return jsonify({'message': 'User deleted successfully'}), 200


@app.route('/api/post', methods=['POST'])
def add_post():
    data = request.get_json()
    title = data['title']
    content = data['content']
    user_id = data['user_id']
    private = data['private']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO post (title, content, user_id, private) VALUES (?, ?, ?, ?)",
                   (title, content, user_id, private))
    post_id = cursor.lastrowid

    conn.commit()
    cursor.close()

    return jsonify({'post_id': post_id}), 201


@app.route('/api/post/<int:post_id>', methods=['PUT'])
def update_post(post_id):
    user_id = int(request.headers.get('Authorization') or 0)
    data = request.get_json()
    title = data['title']
    content = data['content']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM post WHERE id = ?', (post_id,))
    owner = cursor.fetchone()
    if owner:
        owner_id = owner[0]
        if owner_id != user_id:
            abort(403)
        cursor.execute("UPDATE post SET title=?, content=? WHERE id=?", (title, content, post_id))

        conn.commit()
        cursor.close()

        return jsonify({'message': 'Post updated successfully'}), 200
    else:
        return jsonify({'message': 'Post not found'}), 404


@app.route('/api/post/<int:post_id>', methods=['GET'])
def get_post(post_id):
    user_id = int(request.headers.get('Authorization') or 0)
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT post.id, post.title, post.content, post.user_id, COUNT(like.id) as num_likes
    FROM post
    LEFT JOIN like ON post.id = like.post_id
    WHERE (post.private = 1 or post.user_id = ?) AND post.id = ?
    GROUP BY post.id
    ''', (user_id, post_id))

    post = cursor.fetchone()
    cursor.close()

    if post:
        post_data = {
            'id': post[0],
            'title': post[1],
            'content': post[2],
            'user_id': post[3],
            'num_likes': post[4]
        }
        return jsonify(post_data), 200
    else:
        return jsonify({'message': 'Post not found'}), 404


@app.route('/api/post/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    user_id = int(request.headers.get('Authorization') or 0)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM post WHERE id = ?', (post_id,))
    owner = cursor.fetchone()
    if owner:
        owner_id = owner[0]
        if owner_id != user_id:
            abort(403)
        cursor.execute("DELETE FROM post WHERE id=?", (post_id,))

        conn.commit()
        cursor.close()

        return jsonify({'message': 'Post deleted successfully'}), 200
    else:
        return jsonify({'message': 'Post not found'}), 404


@app.route('/api/posts', methods=['GET'])
def get_all_posts():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    SELECT post.id, post.title, post.content, post.user_id, COUNT(like.id) as num_likes
    FROM post
    LEFT JOIN like ON post.id = like.post_id
    WHERE post.private = 1
    GROUP BY post.id
    ''')

    posts = []
    for row in cursor.fetchall():
        post = {
            'id': row[0],
            'title': row[1],
            'content': row[2],
            'user_id': row[3],
            'num_likes': row[4]
        }
        posts.append(post)

    cursor.close()

    return jsonify(posts), 200


@app.route('/api/like', methods=['POST'])
def add_like():
    data = request.get_json()
    post_id = data['post_id']
    user_id = data['user_id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO like (post_id, user_id) VALUES (?, ?)", (post_id, user_id))
    like_id = cursor.lastrowid

    conn.commit()
    cursor.close()

    return jsonify({'like_id': like_id}), 201


@app.route('/api/like/<int:post_id>', methods=['DELETE'])
def delete_like(post_id):
    user_id = int(request.headers.get('Authorization') or 0)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM like WHERE post_id=? AND user_id=?", (post_id, user_id))

    conn.commit()
    cursor.close()

    return jsonify({'message': 'Like deleted successfully'}), 200


if __name__ == '__main__':
    app.run(debug=True, port=9001)
