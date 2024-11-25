import os
import json
import socket
from datetime import datetime
from flask import Flask, render_template, request, send_from_directory, abort
import threading
import time

# Конфігурація
HTTP_PORT = 3000
SOCKET_PORT = 7000
STORAGE_DIR = 'storage'
DATA_FILE = os.path.join(STORAGE_DIR, 'data.json')

# Переконаємося, що папка для збереження даних існує
os.makedirs(STORAGE_DIR, exist_ok=True)

# Ініціалізація Flask-додатку
app = Flask(__name__)

# Глобальна змінна для контролю стану потоку
SOCKET_THREAD_STARTED = False
SOCKET_THREAD = None  # Додатково, щоб зберігати сам потік

# Маршрути
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/message', methods=['GET', 'POST'])
def message():
    if request.method == 'POST':
        username = request.form.get('username', 'Anonymous')
        message = request.form.get('message', '')
        send_to_socket_server(username, message)
        return render_template('message.html', success=True)
    return render_template('message.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    static_dir = os.path.join(app.root_path, 'static')
    return send_from_directory(static_dir, filename)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html'), 404

# Функція для відправки даних на Socket сервер
def send_to_socket_server(username, message):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        data = json.dumps({"username": username, "message": message}).encode('utf-8')
        sock.sendto(data, ('127.0.0.1', SOCKET_PORT))

# Socket сервер
def socket_server():
    global SOCKET_THREAD_STARTED
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(('127.0.0.1', SOCKET_PORT))
            print(f"Socket сервер запущено на порту {SOCKET_PORT}")
            SOCKET_THREAD_STARTED = True  # Мітка, що сервер запущено

            while True:
                data, _ = sock.recvfrom(1024)
                message_dict = json.loads(data.decode('utf-8'))
                save_to_json(message_dict)
    except OSError as e:
        print(f"Socket сервер не зміг запуститися: {e}")
        SOCKET_THREAD_STARTED = False  # Якщо сталася помилка, сервер не запущений

# Функція для збереження даних у файл JSON
def save_to_json(message_dict):
    timestamp = datetime.now().isoformat()
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {}

        data[timestamp] = message_dict

        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Повідомлення збережено: {message_dict}")
    except Exception as e:
        print(f"Помилка збереження даних: {e}")

# Функція для зупинки потоку
def stop_socket_thread():
    global SOCKET_THREAD
    if SOCKET_THREAD and SOCKET_THREAD.is_alive():
        SOCKET_THREAD.join()  # Чекаємо на завершення потоку

# Запуск серверів у потоках
def main():
    global SOCKET_THREAD_STARTED, SOCKET_THREAD

    # Перевіряємо, чи Socket сервер вже запущений
    if not SOCKET_THREAD_STARTED:
        SOCKET_THREAD = threading.Thread(target=socket_server, name="SocketServerThread", daemon=True)
        SOCKET_THREAD.start()
        print("Socket сервер запущено.")
    else:
        print("Socket сервер вже запущений.")

    # Запускаємо Flask сервер
    app.run(port=HTTP_PORT, debug=True, use_reloader=False)  # use_reloader=False, щоб уникнути автоматичного перезавантаження Flask

if __name__ == '__main__':
    try:
        # Переконайтеся, що потік ще не запущений
        if not SOCKET_THREAD_STARTED:
            main()
    except KeyboardInterrupt:
        print("Програма завершена.")
        stop_socket_thread()  # Завершуємо потік перед виходом
