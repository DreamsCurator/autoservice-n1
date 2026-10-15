class NotFound(Exception):
    """Запись не найдена."""


class Conflict(Exception):
    """Запись конфликтует с уже существующей."""


class InvalidData(Exception):
    """Данные не проходят ограничение таблицы."""
