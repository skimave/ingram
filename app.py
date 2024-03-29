from flask import Flask, request, jsonify, send_from_directory, Response
import os, uuid, io
from PIL import Image, ImageOps, ImageSequence
import imghdr
from datetime import datetime, timedelta
from urllib.parse import urlparse
import config

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024


def validate_image(image_data):
    # Image type check
    format = imghdr.what(None, image_data)
    if format == 'jpeg':
        return '.jpeg'
    elif format == 'gif':
        return '.gif'
    else:
        return None

@app.route(f'/{config.SECRET_URL_PATH}/image.gif', methods=['PUT'])
@app.route(f'/{config.SECRET_URL_PATH}/image.jpeg', methods=['PUT'])
def upload_fixed_path_image():
    if request.content_type not in ['image/jpeg', 'image/gif']:
        return "Unsupported media type", 415

    image_data = request.data
    if not image_data:
        return "No image data received", 400

    try:
        # Image identification
        file_extension = validate_image(image_data)
        if file_extension is None:
            return jsonify({"error": "Invalid image file."}), 400

        # Pregenerate a filename
        filename = f"{uuid.uuid4()}{file_extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        with Image.open(io.BytesIO(image_data)) as img:
            if file_extension == ".gif":
            # Ensure it's actually an animated GIF
                if img.is_animated:
                    frames = []
                    durations = []
                    for frame in ImageSequence.Iterator(img):
                        # Copy the frame to work with it and preserve its properties
                        new_frame = frame.copy()
                        frames.append(new_frame)
                        # Horrible but it works. This is due to the IRC client messing with the frame duration information :|
                        durations.append(66)

                    # Save all frames to a new file
                    frames[0].save(filepath, save_all=True, append_images=frames[1:], optimize=False, loop=0, format='GIF', duration=durations)
            else:
                # It's a JPG...
                #Rotation fixes
                img = ImageOps.exif_transpose(img)
                img.save(filepath)

        # Close finally
        img.close()

        # URI to be returned
        image_uri = request.host_url + 'image/' + filename
        parsed_url = urlparse(image_uri)
        secure_uri = parsed_url._replace(scheme="https").geturl()

        # A format that Palaver accepts
        response = Response(secure_uri, mimetype='text/uri-list')
        return response
    except IOError:
        return "Failed to process the image", 400

@app.route('/', methods=['GET'])
def index():
    return jsonify({'UWU': 'OwO'}), 200

@app.errorhandler(404)
def not_found(e):
    return jsonify({'Not': 'Found'}), 200

@app.route('/image/<filename>', methods=['GET'])
def get_image(filename):
    # Sanitize...
    filename = os.path.basename(filename)
    # Check if file is old enough for pending deletion
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        last_modified_time = os.path.getmtime(file_path)
        last_modified_date = datetime.fromtimestamp(last_modified_time)
        current_time = datetime.now()
        age = current_time - last_modified_date

        # Check if the file is less than configured days old
        if age > timedelta(days=config.DAYS_OLD):
            # Delete the file
            os.remove(file_path)
    else:
        return jsonify({'Not': 'Found'}), 200
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run()
