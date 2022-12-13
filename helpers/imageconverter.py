import base64


class ImageConverter:
    def __init__(self) -> None:
        pass

    def convert_image_to_base64(self, image_path):
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
        return encoded_string

    def convert_base64_to_image(self, base64_string, image_path):
        with open(image_path, "wb") as fh:
            fh.write(base64.decodebytes(base64_string))
