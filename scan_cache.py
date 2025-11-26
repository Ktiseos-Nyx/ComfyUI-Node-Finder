"""
Cache manager for ComfyUI node scan results.
Stores scan results and detects when custom_nodes directory changes.
"""

import json
import hashlib
import pickle
from pathlib import Path
from typing import Dict, Set, Optional, Tuple


class ScanCache:
    """Manages caching of ComfyUI node scan results."""
    
    def __init__(self, cache_dir: str = ".cache"):
        """
        Initialize the scan cache.
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        self.hash_file = self.cache_dir / "custom_nodes_hash.txt"
        self.builtin_cache = self.cache_dir / "builtin_nodes.pkl"
        self.custom_cache = self.cache_dir / "custom_nodes.pkl"
        self.metadata_cache = self.cache_dir / "scan_metadata.json"
    
    def get_custom_nodes_hash(self, comfyui_path: str) -> Optional[str]:
        """
        Calculate hash of custom_nodes directory structure.
        
        Args:
            comfyui_path: Path to ComfyUI installation
            
        Returns:
            MD5 hash of directory names, or None if directory doesn't exist
        """
        custom_nodes_dir = Path(comfyui_path) / "custom_nodes"
        
        if not custom_nodes_dir.exists():
            return None
        
        # Get sorted list of directory names (excluding hidden dirs and __pycache__)
        dirs = sorted([
            d.name for d in custom_nodes_dir.iterdir() 
            if d.is_dir() and not d.name.startswith('.') and d.name != '__pycache__'
        ])
        
        # Create hash from directory names
        hash_str = "|".join(dirs)
        return hashlib.md5(hash_str.encode()).hexdigest()
    
    def has_changed(self, comfyui_path: str) -> bool:
        """
        Check if custom_nodes directory has changed since last scan.
        
        Args:
            comfyui_path: Path to ComfyUI installation
            
        Returns:
            True if directory changed or no cache exists
        """
        current_hash = self.get_custom_nodes_hash(comfyui_path)
        
        if current_hash is None:
            return True  # Directory doesn't exist, force scan
        
        if not self.hash_file.exists():
            return True  # No cache, need to scan
        
        try:
            stored_hash = self.hash_file.read_text().strip()
            return current_hash != stored_hash
        except Exception:
            return True  # Error reading cache, force scan
    
    def save_hash(self, comfyui_path: str):
        """
        Save current custom_nodes directory hash.
        
        Args:
            comfyui_path: Path to ComfyUI installation
        """
        current_hash = self.get_custom_nodes_hash(comfyui_path)
        if current_hash:
            self.hash_file.write_text(current_hash)
    
    def save_scan_results(
        self, 
        builtin_nodes: Set[str], 
        custom_nodes: Dict[str, str],
        comfyui_path: str
    ):
        """
        Save scan results to cache.
        
        Args:
            builtin_nodes: Set of built-in node class names
            custom_nodes: Dict mapping node class names to repository names
            comfyui_path: Path to ComfyUI installation
        """
        try:
            # Save builtin nodes
            with open(self.builtin_cache, 'wb') as f:
                pickle.dump(builtin_nodes, f)
            
            # Save custom nodes
            with open(self.custom_cache, 'wb') as f:
                pickle.dump(custom_nodes, f)
            
            # Save metadata
            metadata = {
                'comfyui_path': str(comfyui_path),
                'builtin_count': len(builtin_nodes),
                'custom_count': len(custom_nodes),
                'total_repos': len(set(custom_nodes.values()))
            }
            with open(self.metadata_cache, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Save hash
            self.save_hash(comfyui_path)
            
        except Exception as e:
            print(f"⚠ Warning: Failed to save scan cache: {e}")
    
    def load_scan_results(self) -> Optional[Tuple[Set[str], Dict[str, str]]]:
        """
        Load cached scan results.
        
        Returns:
            Tuple of (builtin_nodes, custom_nodes) or None if cache doesn't exist
        """
        if not self.builtin_cache.exists() or not self.custom_cache.exists():
            return None
        
        try:
            # Load builtin nodes
            with open(self.builtin_cache, 'rb') as f:
                builtin_nodes = pickle.load(f)
            
            # Load custom nodes
            with open(self.custom_cache, 'rb') as f:
                custom_nodes = pickle.load(f)
            
            return builtin_nodes, custom_nodes
            
        except Exception as e:
            print(f"⚠ Warning: Failed to load scan cache: {e}")
            return None
    
    def get_metadata(self) -> Optional[Dict]:
        """
        Get cached scan metadata.
        
        Returns:
            Metadata dict or None if not available
        """
        if not self.metadata_cache.exists():
            return None
        
        try:
            with open(self.metadata_cache, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def clear_cache(self):
        """Clear all cache files."""
        for cache_file in [self.hash_file, self.builtin_cache, self.custom_cache, self.metadata_cache]:
            if cache_file.exists():
                cache_file.unlink()
    
    def cache_exists(self) -> bool:
        """Check if cache files exist."""
        return (
            self.hash_file.exists() and 
            self.builtin_cache.exists() and 
            self.custom_cache.exists()
        )
