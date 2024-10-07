import random
import sqlite3
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

# Подключение к базе данных
def init_db():
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS words (id INTEGER PRIMARY KEY, word TEXT)''')
    conn.commit()
    conn.close()

init_db()  # Инициализация базы данных

# Получение списка слов из базы данных
def get_words():
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    c.execute('SELECT word FROM words')
    words = [row[0] for row in c.fetchall()]
    conn.close()
    return words

# Добавление нового слова в базу данных
def add_word(word):
    conn = sqlite3.connect('words.db')
    c = conn.cursor()
    c.execute('INSERT INTO words (word) VALUES (?)', (word,))
    conn.commit()
    conn.close()

# Изначальный список слов
word_list = [
    "привет", "мир", "слово", "кот", "собака", "машина", "дерево", "человек"
]

chosen_word = ""
correct_guesses = []
attempts = 0
previous_guesses = set()  # Храним предыдущие попытки

@app.route('/')
def index():
    global chosen_word, correct_guesses, attempts, previous_guesses

    # Получаем все слова из базы данных и объединяем с изначальным списком
    full_word_list = word_list + get_words()

    chosen_word = random.choice(full_word_list)
    correct_guesses = ["_" for _ in chosen_word]
    attempts = 0
    previous_guesses.clear()  # Очищаем предыдущие попытки для новой игры
    return render_template('index.html', word_length=len(chosen_word), correct_guesses=correct_guesses, attempts=attempts)


@app.route('/guess', methods=['POST'])
def guess():
    global chosen_word, correct_guesses, attempts, previous_guesses
    guess_word = request.json['guess_word'].lower()

    # Проверяем наличие слова в списке и базе данных
    if guess_word not in word_list + get_words():
        add_word(guess_word)  # Добавляем слово в базу, если его нет
        socketio.emit('new_word', {'word': guess_word}, broadcast=True)  # Обновляем список слов в реальном времени

    # Проверка на длину слова
    if len(guess_word) <= len(chosen_word):
        if guess_word not in previous_guesses:  # Игнорируем повторные попытки
            attempts += 1
            previous_guesses.add(guess_word)  # Добавляем слово в предыдущие попытки

            for i, letter in enumerate(chosen_word[:len(guess_word)]):
                if letter == guess_word[i]:
                    correct_guesses[i] = letter

            if ''.join(correct_guesses) == chosen_word:
                return jsonify({"status": "win", "chosen_word": chosen_word, "attempts": attempts})

        return jsonify({"status": "continue", "correct_guesses": correct_guesses, "attempts": attempts})
    else:
        return jsonify({"status": "error", "message": "Неверная длина слова"})


@app.route('/give_up')
def give_up():
    return jsonify({"status": "give_up", "chosen_word": chosen_word})

@socketio.on('connect')
def on_connect():
    # Отправляем все слова при подключении
    all_words = word_list + get_words()
    emit('word_list', {'words': all_words})

@socketio.on('send_message')
def handle_send_message(data):
    emit('receive_message', data, broadcast=True)  # Отправляем сообщение всем подключённым клиентам

if __name__ == '__main__':
    socketio.run(app, debug=True)
