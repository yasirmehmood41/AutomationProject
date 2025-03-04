from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Dummy data representing scenes for preview
scenes = [
    {"scene_number": 1, "text": "Scene 1: Introduce product.", "duration": 5},
    {"scene_number": 2, "text": "Scene 2: Showcase benefits.", "duration": 5},
    {"scene_number": 3, "text": "Scene 3: Conclude with a call-to-action.", "duration": 5}
]

@app.route('/')
def preview_dashboard():
    # Render a basic preview of scenes (Create a simple HTML template for this)
    return render_template('preview.html', scenes=scenes)

@app.route('/update', methods=['POST'])
def update_scene():
    # Process manual updates (for now, just print the changes)
    scene_number = request.form.get("scene_number")
    new_text = request.form.get("new_text")
    # Here you would update your scene data; for demo, we just print
    print(f"Scene {scene_number} updated to: {new_text}")
    return redirect(url_for('preview_dashboard'))

if __name__ == "__main__":
    # Run the Flask app for manual interface testing
    app.run(debug=True)
