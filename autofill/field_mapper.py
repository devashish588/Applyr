"""
Field mapper - Maps form labels to profile.json keys
"""
from typing import Dict, Any
from utils.profile_loader import get_profile


class FieldMapper:
    """Map job portal form fields to user profile data."""
    
    def __init__(self):
        self.profile = get_profile()
        self.field_mapping = self._build_default_mapping()
    
    def _build_default_mapping(self) -> Dict[str, str]:
        """Build default field mappings."""
        personal = self.profile.get_personal_info()
        
        return {
            # Common form field names
            "fullName": personal.get("name", ""),
            "full_name": personal.get("name", ""),
            "name": personal.get("name", ""),
            "firstName": personal.get("name", "").split()[0] if personal.get("name") else "",
            "first_name": personal.get("name", "").split()[0] if personal.get("name") else "",
            "lastName": personal.get("name", "").split()[-1] if personal.get("name") else "",
            "last_name": personal.get("name", "").split()[-1] if personal.get("name") else "",
            
            "email": personal.get("email", ""),
            "emailAddress": personal.get("email", ""),
            "email_address": personal.get("email", ""),
            
            "phone": personal.get("phone", ""),
            "phoneNumber": personal.get("phone", ""),
            "phone_number": personal.get("phone", ""),
            "mobile": personal.get("phone", ""),
            
            "linkedin": personal.get("linkedin", ""),
            "linkedIn": personal.get("linkedin", ""),
            "linkedin_url": personal.get("linkedin", ""),
            "linkedinUrl": personal.get("linkedin", ""),
            
            "github": personal.get("github", ""),
            "gitHub": personal.get("github", ""),
            "github_url": personal.get("github", ""),
            "githubUrl": personal.get("github", ""),
            
            "portfolio": personal.get("portfolio", ""),
            "portfolioUrl": personal.get("portfolio", ""),
            "portfolio_url": personal.get("portfolio", ""),
            "website": personal.get("portfolio", ""),
            
            "city": personal.get("city", ""),
            "location": personal.get("city", ""),
            
            "pincode": personal.get("pincode", ""),
            "zipcode": personal.get("pincode", ""),
            "zip": personal.get("pincode", ""),
            "postalCode": personal.get("pincode", ""),
            "postal_code": personal.get("pincode", ""),
        }
    
    def get_field_value(self, field_name: str) -> str:
        """Get profile value for field name."""
        return self.field_mapping.get(field_name, "")
    
    def detect_and_map_fields(self, form_labels: list) -> Dict[str, str]:
        """
        Detect form fields and return mapped values.
        
        Args:
            form_labels: List of form field labels/names
        
        Returns:
            Dict mapping field names to profile values
        """
        mapped = {}
        for field in form_labels:
            value = self.get_field_value(field)
            if value:
                mapped[field] = value
        
        return mapped
