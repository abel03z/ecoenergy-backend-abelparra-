from django.core.exceptions import ValidationError


class ComplexityPasswordValidator:
    """
    Exige mayúscula, minúscula, número y carácter especial.
    La longitud mínima (10) la valida MinimumLengthValidator de Django;
    ambos se configuran en AUTH_PASSWORD_VALIDATORS.
    """

    def validate(self, password, user=None):
        errors = []
        if not any(c.isupper() for c in password):
            errors.append(ValidationError(
                "La contraseña debe incluir al menos una letra mayúscula.",
                code="password_no_upper",
            ))
        if not any(c.islower() for c in password):
            errors.append(ValidationError(
                "La contraseña debe incluir al menos una letra minúscula.",
                code="password_no_lower",
            ))
        if not any(c.isdigit() for c in password):
            errors.append(ValidationError(
                "La contraseña debe incluir al menos un número.",
                code="password_no_digit",
            ))
        if not any(not c.isalnum() and not c.isspace() for c in password):
            errors.append(ValidationError(
                "La contraseña debe incluir al menos un carácter especial (por ejemplo ! @ # $ % *).",
                code="password_no_special",
            ))
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            "Debe incluir al menos una mayúscula, una minúscula, "
            "un número y un carácter especial."
        )
