from flask import Flask, render_template, Response, jsonify, request, redirect, url_for, session
import cv2
import mediapipe as mp
import numpy as np
import time
from datetime import datetime
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = 'your_secret_key'  


client = MongoClient('mongodb://localhost:27017')
db = client['MINI_PROJECT1']
users_collection = db['ALEX']


mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils


count = 0
target_count = 0
position = None
exercise_started = False
feedback_message = "Begin PostureTraining!"
start_time = None
last_rep_time = None
exercise = None

# Calculate angle between three points
def calculate_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)

    ba = a - b
    bc = c - b

    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))

    return np.degrees(angle)

# Generate video frames
def generate_frames():
    global count, position, exercise_started, feedback_message, start_time, last_rep_time, exercise
    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image)

        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.pose_landmarks and exercise_started and exercise:
            landmarks = results.pose_landmarks.landmark

            joints = exercise["joints"]
            coords = [
                [landmarks[getattr(mp_pose.PoseLandmark, joint).value].x,
                 landmarks[getattr(mp_pose.PoseLandmark, joint).value].y]
                for joint in joints
            ]

            angle = calculate_angle(*coords)

            if angle > exercise["target_angle"] + exercise["threshold"]:
                position = "up"
            if position == "up" and angle < exercise["target_angle"] - exercise["threshold"]:
                position = "down"
                count += 1

                current_time = time.time()
                if last_rep_time:
                    rep_time = current_time - last_rep_time
                    if exercise["optimal_speed_range"][0] <= rep_time <= exercise["optimal_speed_range"][1]:
                        feedback_message = "Good speed! Keep going."
                    elif rep_time < exercise["optimal_speed_range"][0]:
                        feedback_message = "Too fast! Slow down."
                    else:
                        feedback_message = "Too slow! Speed up."
                last_rep_time = current_time

                # Start timer for the first rep
                if count == 1:
                    start_time = current_time

            if angle < exercise["target_angle"] - exercise["threshold"]:
                feedback_message = "Lower your knee slightly"
            elif angle > exercise["target_angle"] + exercise["threshold"]:
                feedback_message = "Raise your knee higher!"

         
            cv2.putText(image, f'Angle: {int(angle)}', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(image, f'Count: {count}/{target_count}', (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            cv2.putText(image, feedback_message, (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        
            if count >= target_count:
                exercise_started = False
                total_time = time.time() - start_time if start_time else 0
                feedback_message = f"PostureTraining Complete! Total time: {total_time:.2f}s"
                cv2.putText(image, feedback_message, (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                if 'username' in session:
                    session_data = {
                        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "count": count,
                        "total_time": total_time,
                        "average_speed": total_time / count if count > 0 else 0
                    }
                    users_collection.update_one(
                        {"username": session['username']},
                        {"$push": {"sessions": session_data}}
                    )

                start_time = None
                last_rep_time = None
                count = 0

        # Encode the frame and send to the frontend
        ret, buffer = cv2.imencode('.jpg', image)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('profile'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({"username": username, "password": password})
        if user:
            session['username'] = username
            return redirect(url_for('profile'))
        else:
            return render_template('login.html', error="Invalid username or password.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        age = request.form['age']
        height = request.form['height']
        weight = request.form['weight']
        blood_group = request.form['blood_group']

        if users_collection.find_one({"username": username}):
            return render_template('register.html', error="Username already exists.")

        user_data = {
            "username": username,
            "password": password,
            "age": age,
            "height": height,
            "weight": weight,
            "blood_group": blood_group,
            "sessions": []
        }
        users_collection.insert_one(user_data)
        session['username'] = username
        return redirect(url_for('profile'))
    return render_template('register.html')

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = users_collection.find_one({"username": session['username']})
    if not user:
        return redirect(url_for('login'))

    # Prepare data for charts
    session_dates = [session['date'] for session in user['sessions']]
    session_counts = [session['count'] for session in user['sessions']]
    session_total_times = [session['total_time'] for session in user['sessions']]
    session_average_speeds = [session['average_speed'] for session in user['sessions']]

    return render_template('profile.html',
                           user=user,
                           session_dates=session_dates,
                           session_counts=session_counts,
                           session_total_times=session_total_times,
                           session_average_speeds=session_average_speeds)

@app.route('/admin')
def admin():
    if 'username' not in session or session['username'] != 'ALEX J MATHEW':
        return redirect(url_for('login'))
    users = list(users_collection.find({}))
    return render_template('admin.html', users=users)


@app.route('/save_session', methods=['POST'])
def save_session():
    global count, start_time, last_rep_time
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'User not logged in'})

    if count == 0:
        return jsonify({'success': False, 'error': 'No exercise data to save'})

    total_time = time.time() - start_time if start_time else 0
    session_data = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": count,
        "total_time": total_time,
        "average_speed": total_time / count if count > 0 else 0
    }
    users_collection.update_one(
        {"username": session['username']},
        {"$push": {"sessions": session_data}}
    )
    return jsonify({'success': True})
@app.template_filter('mean')
def mean_filter(values):
    if not values:
        return 0
    return sum(values) / len(values)

# Register the filter
app.jinja_env.filters['mean'] = mean_filter
@app.route('/recommendations')
def recommendations():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = users_collection.find_one({"username": session['username']})
    if not user or 'sessions' not in user or len(user['sessions']) == 0:
        return render_template('recommendation.html', error="No session data found.")

    # Calculate average speed
    avg_speed = np.mean([session['average_speed'] for session in user['sessions'] if session['average_speed'] > 0])

    # Rule-based recommendations
    recommendations = []
    if avg_speed < 1.5:
        recommendations.append("Your speed is too fast. Focus on controlled movements to improve form.")
    if avg_speed > 3.0:
        recommendations.append("Your speed is too slow. Try to increase your pace for better endurance.")
    if not recommendations:
        recommendations.append("Great job! Keep up the good work and aim for consistency.")

    return render_template('recommendation.html', recommendations=recommendations, user=user, avg_speed=avg_speed)

@app.route('/select_exercise', methods=['GET', 'POST'])
def select_exercise():
    if 'username' not in session:
        return redirect(url_for('login'))
    global exercise
    if request.method == 'POST':
        exercise_name = request.form['exercise']
        if exercise_name == "knee_raises":
            exercise = {
                "joints": ["LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"],
                "target_angle": 60,  
                "threshold": 15,
                "optimal_speed_range": (1.0, 2.5)  
            }
        elif exercise_name == "squats":
            exercise = {
                "joints": ["LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE"],
                "target_angle": 90,  
                "threshold": 15,
                "optimal_speed_range": (2.0, 4.0)  
            }
        return redirect(url_for('training'))
    return render_template('select_exercise.html')

@app.route('/training')
def training():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('training.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_count')
def get_count():
    global count, target_count, feedback_message
    return jsonify({'count': count, 'target': target_count, 'feedback': feedback_message})

@app.route('/set_target', methods=['POST'])
def set_target():
    global target_count, count, exercise_started, feedback_message, start_time, last_rep_time
    data = request.json
    target_count = int(data.get('target', 0))
    count = 0
    exercise_started = True
    feedback_message = "Begin PostureTraining!"
    start_time = None
    last_rep_time = None
    return jsonify({'success': True, 'target': target_count})

if __name__ == "__main__":
    app.run(debug=True)
