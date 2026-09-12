from app.shared.domain.validation import DomainValidator
class OrganizationApplicationValidator:
    @staticmethod
    def validate(name,slug):
        if not isinstance(name,str) or not name.strip(): raise ValueError('name is required')
        if not isinstance(slug,str) or not slug.strip(): raise ValueError('slug is required')
        return True
