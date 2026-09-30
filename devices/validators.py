from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def validate_real_image(image):
    """Comprueba que el contenido sea realmente una imagen, sin fiarse de la extensión."""
    try:
        with Image.open(image) as picture:
            picture.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("El archivo no es una imagen válida.")
    finally:
        image.seek(0)
    return image
