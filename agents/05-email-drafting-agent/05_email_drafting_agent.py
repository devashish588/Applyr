"""
Email drafting agent - composes personalized cold emails.
"""

import re


class EmailDraftingAgent:
    """Drafts personalized cold emails for job applications."""
    
    def __init__(self):
        self.default_recipient = None
    
    def draft_email(self, job_data: dict, profile: dict) -> dict:
        """
        Draft personalized cold email for a specific job.
        
        Args:
            job_data: {
                "title": "Senior Python Developer",
                "company": "Acme Corp",
                "url": "https://...",
                "jd_text": "Full job description"
            }
            profile: User profile from profile.json
        
        Returns:
            {
                "subject": "Application: Senior Python Developer at Acme Corp",
                "body": "Full email body text"
            }
        """
        personal = profile.get("personal", {})
        name = personal.get("name", "Your Name")
        email = personal.get("email", "")
        phone = personal.get("phone", "")
        linkedin = personal.get("linkedin", "")

        title = job_data.get("title") or "the role"
        company = job_data.get("company") or "your team"
        recipient = job_data.get("hr_email") or self.default_recipient
        skills = self._skills_for_job(job_data, profile)
        achievements = profile.get("key_achievements", [])[:2]

        subject = f"Application: {title} - {name}"
        if company and company != "your team":
            subject = f"Application: {title} at {company} - {name}"

        skills_sentence = ""
        if skills:
            skills_sentence = f"My background in {', '.join(skills[:5])} maps closely to the role. "

        achievement_sentence = ""
        if achievements:
            achievement_sentence = "A couple of relevant highlights: " + "; ".join(achievements) + ". "

        body = (
            f"Hi {company} hiring team,\n\n"
            f"I am applying for the {title} role. "
            f"{skills_sentence}{achievement_sentence}"
            "I would be glad to bring the same mix of ownership, engineering depth, "
            "and product-minded execution to your team.\n\n"
            "I have attached my resume and cover letter for review. "
            "Happy to share more context or discuss fit whenever convenient.\n\n"
            f"Best,\n{name}\n"
        )
        contact_bits = [bit for bit in [email, phone, linkedin] if bit]
        if contact_bits:
            body += "\n" + " | ".join(contact_bits)

        return {
            "to": recipient,
            "subject": subject,
            "body": body,
        }
    
    def personalize_email(self, template: str, replacements: dict) -> str:
        """
        Fill email template with personalized data.
        
        Args:
            template: Email template with {{placeholders}}
            replacements: {"company": "Acme", "role": "Python Dev", ...}
        
        Returns:
            Personalized email text
        """
        result = template
        for key, value in replacements.items():
            result = result.replace("{{" + key + "}}", str(value))
        return result

    def _skills_for_job(self, job_data: dict, profile: dict) -> list[str]:
        profile_skills = []
        skills = profile.get("skills", {})
        for key in ("languages", "frameworks", "tools"):
            profile_skills.extend(skills.get(key, []))

        jd_text = " ".join([
            job_data.get("title", ""),
            job_data.get("description_snippet", ""),
            job_data.get("jd_text", ""),
            " ".join(job_data.get("required_skills", [])),
        ]).lower()

        matched = []
        for skill in profile_skills:
            if re.search(r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])", jd_text):
                matched.append(skill)

        return matched or profile_skills[:5]

    def validate_email(self, email: dict, profile: dict) -> list:
        """
        Validate email content for common mistakes/placeholders before sending.
        """
        warnings = []
        if not email:
            return ["Email is completely empty"]
        
        if not email.get("to"):
            warnings.append("Recipient address is missing")
        if not email.get("subject"):
            warnings.append("Subject is empty")
        if not email.get("body"):
            warnings.append("Body is empty")
            
        body = email.get("body", "")
        subject = email.get("subject", "")
        
        # Check for template remnants
        placeholders = [r"\[.*?\]", r"\{{.*?\}}", r"<.*?>"]
        import re
        for p in placeholders:
            if re.search(p, body) or re.search(p, subject):
                warnings.append(f"Potential placeholder matching '{p}' found in email")
                
        return warnings
