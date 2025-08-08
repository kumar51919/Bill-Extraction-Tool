import cv2
import numpy as np
from flask import Flask, render_template, redirect, request, url_for, Response, session
from flask_uploads import UploadSet, configure_uploads, IMAGES
import os
import requests
from flask_session import Session

app = Flask(__name__)
photos = UploadSet('PHOTOS', IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = 'Uploaded_Bills'
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
configure_uploads(app, photos)

@app.route('/', methods=["GET"], defaults={'name': 'USER'})
def home_page(name):
    return f"<h1>HELLO {name}!\n\tWELCOME TO BILL EXTRACTION.......</h1>"

@app.route('/upload', methods=["POST", "GET"])
def upload():
    if request.method == "POST" and 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        return redirect(url_for("crop_processing"))
    return render_template('uploading.html')

@app.route('/crop_processing', methods=["GET", "POST"])
def crop_processing():
    image_filename = list(os.listdir('Uploaded_Bills'))[0]

    global x_start, y_start, x_end, y_end, cropping
    global j
    j = 0
    cropping = False
    x_start, y_start, x_end, y_end = 0, 0, 0, 0

    image = cv2.imread(os.path.join('Uploaded_Bills', image_filename))
    oriImage = image.copy()

    def mouse_crop(event, x, y, flags, param):
        # grab references to the global variables
        global x_start, y_start, x_end, y_end, cropping, j

        # if the left mouse button was DOWN, start RECORDING
        # (x, y) coordinates and indicate that cropping is being
        if event == cv2.EVENT_LBUTTONDOWN:
            x_start, y_start, x_end, y_end = x, y, x, y
            cropping = True

        # Mouse is Moving
        elif event == cv2.EVENT_MOUSEMOVE:
            if cropping == True:
                x_end, y_end = x, y

        # if the left mouse button was released
        elif event == cv2.EVENT_LBUTTONUP:
            # record the ending (x, y) coordinates
            x_end, y_end = x, y
            cropping = False  # cropping is finished

            refPoint = [(x_start, y_start), (x_end, y_end)]
            j += 1
            if len(refPoint) == 2:  # when two points were found
                roi = oriImage[refPoint[0][1]:refPoint[1][1], refPoint[0][0]:refPoint[1][0]]
                cv2.imwrite("cropped_parts/" + f"{j}.jpg", roi)
                cv2.imshow("cropped", roi)

    cv2.namedWindow("image", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("image", mouse_crop)

    while True:
        i = image.copy()

        if not cropping:
            cv2.imshow("image", image)

        elif cropping:
            cv2.rectangle(i, (x_start, y_start), (x_end, y_end), (255, 0, 0), 2)
            cv2.imshow("image", i)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            os.remove(os.path.join('Uploaded_Bills', str(list(os.listdir('Uploaded_Bills'))[0])))
            break
    cv2.destroyAllWindows()
    return redirect(url_for("extract"))

@app.route('/extract', methods=["GET", "POST"])
def extract():
    images_files = list(os.listdir('cropped_parts'))
    parsed_text = {}
    k = 1
    for image_name in images_files:
        api_key = 'K82379207788957'
        url = 'https://api.ocr.space/parse/image'
        image_path = f"cropped_parts/" + str(image_name)
        payload = {'apikey': api_key, 'language': 'eng'}
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()
        response = requests.post(url, data=payload, files={'image': ('image.jpg', image_data, 'image/jpeg')})
        parsed_text[k] = response.json()["ParsedResults"][0]["ParsedText"]
        k += 1
    session['parsed_text'] = parsed_text
    for image in images_files:
        try:
            os.remove(os.path.join('cropped_parts', str(image)))
        except:
            pass
    API_URL = "http://localhost:3000/api/v1/prediction/04ebddcd-d403-4127-8cba-c35693ddb143"
    response = requests.post(API_URL, json={"question": parsed_text})
    return redirect(url_for('chatAI'))

@app.route('/chatwithai', methods=["GET", "POST"])
def chatAI():
    return render_template('chatAI.html')

if __name__ == '__main__':
    app.run()
