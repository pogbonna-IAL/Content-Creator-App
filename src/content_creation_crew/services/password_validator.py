"""
Password Validation Service
Enforces strong password policies with complexity rules and common password blocking
"""
import re
import logging
from typing import List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class PasswordPolicy:
    """
    Password policy configuration
    
    Configurable via environment variables or code
    """
    def __init__(
        self,
        min_length: int = 8,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_symbol: bool = True,
        block_common_passwords: bool = True,
        common_passwords_file: Optional[str] = None
    ):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_symbol = require_symbol
        self.block_common_passwords = block_common_passwords
        self.common_passwords_file = common_passwords_file
        
        # Load common passwords
        self._common_passwords = set()
        if block_common_passwords:
            self._load_common_passwords()
    
    def _load_common_passwords(self):
        """Load common passwords from file"""
        try:
            # Try custom file first
            if self.common_passwords_file and Path(self.common_passwords_file).exists():
                with open(self.common_passwords_file, 'r') as f:
                    self._common_passwords = {line.strip().lower() for line in f if line.strip()}
                logger.info(f"✓ Loaded {len(self._common_passwords)} common passwords from {self.common_passwords_file}")
                return
            
            # Fall back to built-in list
            default_file = Path(__file__).parent.parent / "data" / "common_passwords.txt"
            if default_file.exists():
                with open(default_file, 'r') as f:
                    self._common_passwords = {line.strip().lower() for line in f if line.strip()}
                logger.info(f"✓ Loaded {len(self._common_passwords)} common passwords from built-in list")
            else:
                logger.warning("Common passwords file not found, using minimal hardcoded list")
                self._common_passwords = self._get_minimal_common_passwords()
        except Exception as e:
            logger.error(f"Failed to load common passwords: {e}")
            self._common_passwords = self._get_minimal_common_passwords()
    
    def _get_minimal_common_passwords(self) -> set:
        """
        Get minimal list of most common passwords (hardcoded fallback)
        
        Top 100 most common passwords from various breaches
        """
        return {
            "password", "123456", "12345678", "1234", "qwerty", "12345", "dragon",
            "pussy", "baseball", "football", "letmein", "monkey", "696969", "abc123",
            "mustang", "michael", "shadow", "master", "jennifer", "111111", "2000",
            "jordan", "superman", "harley", "1234567", "fuckme", "hunter", "fuckyou",
            "trustno1", "ranger", "buster", "thomas", "tigger", "robert", "soccer",
            "fuck", "batman", "test", "pass", "killer", "hockey", "george", "charlie",
            "andrew", "michelle", "love", "sunshine", "jessica", "asshole", "pepper",
            "daniel", "access", "123456789", "654321", "joshua", "maggie", "starwars",
            "silver", "william", "dallas", "yankees", "123123", "ashley", "666666",
            "hello", "amanda", "orange", "biteme", "freedom", "computer", "sexy",
            "thunder", "nicole", "ginger", "heather", "hammer", "summer", "corvette",
            "taylor", "fucker", "austin", "1111", "merlin", "matthew", "121212",
            "golfer", "cheese", "princess", "martin", "chelsea", "patrick", "richard",
            "diamond", "yellow", "bigdog", "secret", "asdfgh", "sparky", "cowboy",
            "camaro", "anthony", "matrix"
        }
    
    def is_common_password(self, password: str) -> bool:
        """Check if password is in common passwords list"""
        return password.lower() in self._common_passwords


class PasswordValidationError(Exception):
    """Password validation failed"""
    def __init__(self, message: str, field: str = "password"):
        self.message = message
        self.field = field
        super().__init__(message)


class PasswordValidator:
    """
    Password validator with configurable policy
    
    Usage:
        validator = PasswordValidator()
        is_valid, error = validator.validate("MyP@ssw0rd")
        if not is_valid:
            raise HTTPException(status_code=400, detail=error)
    """
    
    def __init__(self, policy: Optional[PasswordPolicy] = None):
        self.policy = policy or PasswordPolicy()
    
    def validate(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password against policy
        
        Args:
            password: Password to validate
        
        Returns:
            Tuple of (is_valid, error_message)
            If valid: (True, None)
            If invalid: (False, "error message")
        """
        if not password:
            return False, "Password is required"
        
        # Check minimum length
        if len(password) < self.policy.min_length:
            return False, f"Password must be at least {self.policy.min_length} characters long"
        
        # Check complexity requirements
        errors = []
        
        if self.policy.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("one uppercase letter")
        
        if self.policy.require_lowercase and not re.search(r'[a-z]', password):
            errors.append("one lowercase letter")
        
        if self.policy.require_digit and not re.search(r'\d', password):
            errors.append("one digit")
        
        if self.policy.require_symbol and not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            errors.append("one special character")
        
        if errors:
            if len(errors) == 1:
                return False, f"Password must contain at least {errors[0]}"
            else:
                return False, f"Password must contain at least {', '.join(errors[:-1])} and {errors[-1]}"
        
        # Check against common passwords
        if self.policy.block_common_passwords and self.policy.is_common_password(password):
            # Generic message to avoid information leakage
            return False, "This password is too common. Please choose a more unique password"
        
        return True, None
    
    def validate_or_raise(self, password: str):
        """
        Validate password and raise exception if invalid
        
        Args:
            password: Password to validate
        
        Raises:
            PasswordValidationError: If password is invalid
        """
        is_valid, error = self.validate(password)
        if not is_valid:
            raise PasswordValidationError(error)
    
    def get_requirements_text(self) -> str:
        """
        Get human-readable password requirements text
        
        Returns:
            String describing password requirements
        """
        requirements = [f"At least {self.policy.min_length} characters"]
        
        if self.policy.require_uppercase:
            requirements.append("One uppercase letter")
        
        if self.policy.require_lowercase:
            requirements.append("One lowercase letter")
        
        if self.policy.require_digit:
            requirements.append("One number")
        
        if self.policy.require_symbol:
            requirements.append("One special character (!@#$%^&* etc.)")
        
        if self.policy.block_common_passwords:
            requirements.append("Not a common password")
        
        return " • ".join(requirements)
    
    def get_requirements_list(self) -> List[str]:
        """
        Get password requirements as a list (for API responses)
        
        Returns:
            List of requirement strings
        """
        requirements = [f"At least {self.policy.min_length} characters"]
        
        if self.policy.require_uppercase:
            requirements.append("One uppercase letter (A-Z)")
        
        if self.policy.require_lowercase:
            requirements.append("One lowercase letter (a-z)")
        
        if self.policy.require_digit:
            requirements.append("One number (0-9)")
        
        if self.policy.require_symbol:
            requirements.append("One special character (!@#$%^&* etc.)")
        
        if self.policy.block_common_passwords:
            requirements.append("Not a commonly used password")
        
        return requirements


# Singleton instance
_password_validator: Optional[PasswordValidator] = None


def get_password_validator() -> PasswordValidator:
    """
    Get or create password validator singleton
    
    Configurable via environment variables:
    - PASSWORD_MIN_LENGTH (default: 8)
    - PASSWORD_REQUIRE_UPPERCASE (default: true)
    - PASSWORD_REQUIRE_LOWERCASE (default: true)
    - PASSWORD_REQUIRE_DIGIT (default: true)
    - PASSWORD_REQUIRE_SYMBOL (default: true)
    - PASSWORD_BLOCK_COMMON (default: true)
    - PASSWORD_COMMON_LIST_FILE (optional: path to custom list)
    
    Returns:
        PasswordValidator instance
    """
    global _password_validator
    
    if _password_validator is None:
        import os
        
        # Parse environment variables
        min_length = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
        require_uppercase = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
        require_lowercase = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
        require_digit = os.getenv("PASSWORD_REQUIRE_DIGIT", "true").lower() == "true"
        require_symbol = os.getenv("PASSWORD_REQUIRE_SYMBOL", "true").lower() == "true"
        block_common = os.getenv("PASSWORD_BLOCK_COMMON", "true").lower() == "true"
        common_list_file = os.getenv("PASSWORD_COMMON_LIST_FILE")
        
        policy = PasswordPolicy(
            min_length=min_length,
            require_uppercase=require_uppercase,
            require_lowercase=require_lowercase,
            require_digit=require_digit,
            require_symbol=require_symbol,
            block_common_passwords=block_common,
            common_passwords_file=common_list_file
        )
        
        _password_validator = PasswordValidator(policy)
        
        logger.info(
            f"✓ Password policy: min_length={min_length}, "
            f"uppercase={require_uppercase}, lowercase={require_lowercase}, "
            f"digit={require_digit}, symbol={require_symbol}, "
            f"block_common={block_common}"
        )
    
    return _password_validator

