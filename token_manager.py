"""
Token Manager

Securely store and retrieve GitHub tokens using a .env file.
"""

import os
from pathlib import Path
from typing import Optional


class TokenManager:
    """Manage GitHub token and ComfyUI location storage in .env file."""
    
    def __init__(self, env_file: str = ".env"):
        """
        Initialize token manager.
        
        Args:
            env_file: Path to .env file (default: .env in current directory)
        """
        self.env_file = Path(env_file)
        self.token_key = "GITHUB_TOKEN"
        self.comfyui_key = "COMFYUI_LOCATION"
    
    def save_token(self, token: str) -> bool:
        """
        Save GitHub token to .env file.
        
        Args:
            token: GitHub personal access token
            
        Returns:
            True if saved successfully
        """
        try:
            # Read existing .env content if it exists
            existing_lines = []
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    existing_lines = [
                        line for line in f.readlines() 
                        if not line.startswith(f"{self.token_key}=")
                    ]
            
            # Add/update token
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.writelines(existing_lines)
                f.write(f"{self.token_key}={token}\n")
            
            print(f"✓ Token saved to {self.env_file}")
            return True
            
        except Exception as e:
            print(f"⚠ Failed to save token: {e}")
            return False
    
    def load_token(self) -> Optional[str]:
        """
        Load GitHub token from .env file.
        
        Returns:
            Token string if found, None otherwise
        """
        if not self.env_file.exists():
            return None
        
        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{self.token_key}="):
                        token = line.split('=', 1)[1].strip()
                        if token:
                            return token
            return None
            
        except Exception as e:
            print(f"⚠ Failed to load token: {e}")
            return None
    
    def delete_token(self) -> bool:
        """
        Delete GitHub token from .env file.
        
        Returns:
            True if deleted successfully
        """
        if not self.env_file.exists():
            return True
        
        try:
            # Read all lines except the token line
            with open(self.env_file, 'r', encoding='utf-8') as f:
                lines = [
                    line for line in f.readlines() 
                    if not line.startswith(f"{self.token_key}=")
                ]
            
            # Write back
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            print(f"✓ Token deleted from {self.env_file}")
            return True
            
        except Exception as e:
            print(f"⚠ Failed to delete token: {e}")
            return False
    
    def has_token(self) -> bool:
        """
        Check if a token exists in .env file.
        
        Returns:
            True if token exists
        """
        return self.load_token() is not None
    
    def save_comfyui_location(self, location: str) -> bool:
        """
        Save ComfyUI installation location to .env file.
        
        Args:
            location: Path to ComfyUI installation
            
        Returns:
            True if saved successfully
        """
        try:
            # Read existing .env content if it exists
            existing_lines = []
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    existing_lines = [
                        line for line in f.readlines() 
                        if not line.startswith(f"{self.comfyui_key}=")
                    ]
            
            # Add/update location
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.writelines(existing_lines)
                f.write(f"{self.comfyui_key}={location}\n")
            
            print(f"✓ ComfyUI location saved to {self.env_file}")
            return True
            
        except Exception as e:
            print(f"⚠ Failed to save location: {e}")
            return False
    
    def load_comfyui_location(self) -> Optional[str]:
        """
        Load ComfyUI installation location from .env file.
        
        Returns:
            Location string if found, None otherwise
        """
        if not self.env_file.exists():
            return None
        
        try:
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{self.comfyui_key}="):
                        location = line.split('=', 1)[1].strip()
                        if location:
                            return location
            return None
            
        except Exception as e:
            print(f"⚠ Failed to load location: {e}")
            return None
    
    def get_or_prompt_token(self, auto_use: bool = True) -> Optional[str]:
        """
        Get token from .env or prompt user to enter one.
        
        Args:
            auto_use: If True, automatically use saved token without prompting
        
        Returns:
            Token string or None if user cancels
        """
        # Try to load existing token
        token = self.load_token()
        
        if token:
            if auto_use:
                print(f"✓ Using saved GitHub token from {self.env_file}")
                return token
            else:
                print(f"✓ Found saved token in {self.env_file}")
                use_saved = input("Use saved token? (y/n) [y]: ").strip().lower() or 'y'
                
                if use_saved == 'y':
                    return token
                else:
                    print("Enter a new token:")
        
        # Prompt for new token
        print("\n⚠ GitHub token is REQUIRED for code search API")
        print("Create a token at: https://github.com/settings/tokens")
        print("Required scopes: 'public_repo' or 'repo'\n")
        
        new_token = input("Enter GitHub token (or press Enter to cancel): ").strip()
        
        if not new_token:
            return None
        
        # Ask to save
        save = input("\nSave token for future use? (y/n) [y]: ").strip().lower() or 'y'
        if save == 'y':
            self.save_token(new_token)
        
        return new_token
    
    def get_or_prompt_comfyui_location(self, auto_use: bool = True) -> Optional[str]:
        """
        Get ComfyUI location from .env or prompt user to enter one.
        
        Args:
            auto_use: If True, automatically use saved location without prompting
        
        Returns:
            Location string or None if user skips
        """
        # Try to load existing location
        location = self.load_comfyui_location()
        
        if location:
            if auto_use:
                print(f"✓ Using saved ComfyUI location: {location}")
                return location
            else:
                print(f"✓ Found saved ComfyUI location: {location}")
                use_saved = input("Use saved location? (y/n) [y]: ").strip().lower() or 'y'
                
                if use_saved == 'y':
                    return location
        
        # Prompt for new location
        print("\nEnter ComfyUI installation path (or press Enter to skip):")
        print("Example: D:\\StableDiffusion\\ComfyUI")
        
        new_location = input("ComfyUI location: ").strip().strip('"').strip("'")
        
        if not new_location:
            return None
        
        # Ask to save
        save = input("\nSave location for future use? (y/n) [y]: ").strip().lower() or 'y'
        if save == 'y':
            self.save_comfyui_location(new_location)
        
        return new_location


def main():
    """Example usage and token management CLI."""
    import sys
    
    manager = TokenManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "save":
            token = input("Enter GitHub token to save: ").strip()
            if token:
                manager.save_token(token)
            else:
                print("No token provided")
        
        elif command == "load":
            token = manager.load_token()
            if token:
                print(f"Token found: {token[:8]}...{token[-4:]}")
            else:
                print("No token found")
        
        elif command == "delete":
            manager.delete_token()
        
        elif command == "check":
            if manager.has_token():
                print("✓ Token exists")
            else:
                print("✗ No token found")
        
        else:
            print("Unknown command. Use: save, load, delete, or check")
    
    else:
        print("Token Manager")
        print("=" * 50)
        print("\nCommands:")
        print("  python token_manager.py save   - Save a new token")
        print("  python token_manager.py load   - Display saved token")
        print("  python token_manager.py delete - Delete saved token")
        print("  python token_manager.py check  - Check if token exists")


if __name__ == "__main__":
    main()
