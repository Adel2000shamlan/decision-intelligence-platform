from dataclasses import dataclass
@dataclass(frozen=True)
class SecurityHeaders:
    strict_transport_security:str="max-age=31536000; includeSubDomains"
    content_security_policy:str="default-src 'self'"
    x_content_type_options:str="nosniff"
    x_frame_options:str="DENY"
    referrer_policy:str="no-referrer"
class SecretBoundary:
    FORBIDDEN=frozenset({'password','password_hash','password_digest','salt','secret','refresh_token','access_token','token','token_hash','api_key','private_key','otp','otp_secret','credential','credentials'})
    @classmethod
    def assert_safe(cls,d):
        if not isinstance(d,dict): raise TypeError('mapping required')
        bad=[k for k in d if str(k).lower() in cls.FORBIDDEN]
        if bad: raise ValueError('secret boundary violation')
        return True
    @classmethod
    def sanitize(cls,d): return {k:v for k,v in d.items() if str(k).lower() not in cls.FORBIDDEN}
