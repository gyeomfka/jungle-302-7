# app.py
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, emit, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


# 현재 생성된 방들
rooms = {}

def sessionHandler():
    session.get("room")


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/join', methods=['POST'])
def join():
    session.clear()
    if request.method == "POST":
        room_id = request.form.get("room")
        if not room_id:
            return render_template('index.html', error = "방 ID를 입력해주세요", room_id = room_id)
        
        if room_id not in rooms:
            rooms[room_id] = {"members" : 0, "messages": []}
        
        session["room"] = room_id
    return redirect(url_for("room", room_id=room_id))


@app.route('/room/<room_id>')
def room(room_id):
    # url room_id이랑 session room_id이랑 비교
    if room_id != session.get("room"):
        return render_template('index.html', error = "url != session_id")

    return render_template("room.html", room_id=room_id)


@socketio.on("join")
def handle_join(data):
    room = data["room"]
    user_id = request.sid
    join_room(room)
    rooms[room]["members"] += 1

    emit("user-joined", {"userId": user_id}, room=room, include_self=False)



@socketio.on("signal")
def handle_signal(data):
    to_user = data["to"]
    emit("signal", {**data, "from": request.sid}, room=to_user)


@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return
    
    content = {
        "name": "이름",
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)



# 이게 있어야 disconnect 작동가능 - 소켓 서버 열결 코드는 "join"
@socketio.on("connect")
def connect():
    return

@socketio.on("disconnect")
def disconnect():
    room = session.get('room')
    leave_room(room)
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    user_id = request.sid
    emit("user-left", {"userId": user_id}, room=room)   


@socketio.on("share-screen")
def handle_share_screen(data):
    room = data["room"]
    # Notify everyone else in the room to expect a new track
    emit("screen-shared", {"userId": request.sid}, room=room, include_self=False)

@socketio.on("stop-screen")
def handle_stop_screen(data):
    room = data["room"]
    emit("screen-stopped", {"userId": request.sid}, room=room, include_self=False)

    
if __name__ == "__main__":
    socketio.run(app, debug=True)
