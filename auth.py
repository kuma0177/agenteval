from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from config import settings

_serializer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="client-session")

_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def create_client_session(job_id: str) -> str:
    return _serializer.dumps(job_id)


def verify_client_session(token: str):
    try:
        return _serializer.loads(token, max_age=_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
