"""
ComfyUI Scanner

Scans a local ComfyUI installation to identify built-in and custom node classes.
"""

import ast
import warnings
from pathlib import Path
from typing import Dict, Set, Optional
from scan_cache import ScanCache

# Suppress SyntaxWarnings from parsing custom node files
warnings.filterwarnings('ignore', category=SyntaxWarning)


class ComfyUIScanner:
    """Scanner for ComfyUI installation to identify node classes."""
    
    def __init__(self, comfyui_path: Optional[str] = None, use_cache: bool = True):
        """
        Initialize the ComfyUI scanner.
        
        Args:
            comfyui_path: Path to ComfyUI installation (will prompt if not provided)
            use_cache: Whether to use cached scan results
        """
        self.comfyui_path = None
        self.builtin_nodes = set()
        self.custom_nodes = {}  # {class_name: repo_path}
        self.use_cache = use_cache
        self.cache = ScanCache() if use_cache else None
        
        if comfyui_path:
            self.set_comfyui_path(comfyui_path)
    
    def set_comfyui_path(self, path: str) -> bool:
        """
        Set and validate ComfyUI installation path.
        
        Args:
            path: Path to ComfyUI installation
            
        Returns:
            True if valid ComfyUI installation
        """
        path = Path(path).resolve()
        
        # Check for ComfyUI markers
        if not path.exists():
            print(f"⚠ Path does not exist: {path}")
            return False
        
        # Look for typical ComfyUI structure
        if not (path / "nodes.py").exists() and not (path / "comfy").exists():
            print(f"⚠ Does not appear to be a ComfyUI installation: {path}")
            return False
        
        self.comfyui_path = path
        print(f"✓ ComfyUI installation found: {path}")
        return True
    
    def prompt_for_path(self, token_manager=None, auto_use: bool = True) -> bool:
        """
        Prompt user for ComfyUI installation path.
        
        Args:
            token_manager: Optional TokenManager to load/save location
            auto_use: If True, automatically use saved location without prompting
        
        Returns:
            True if valid path provided
        """
        # Try to use TokenManager if provided
        if token_manager:
            location = token_manager.get_or_prompt_comfyui_location(auto_use=auto_use)
            if location:
                return self.set_comfyui_path(location)
            return False
        
        # Fallback to manual prompt
        print("\nTo identify built-in vs custom nodes, provide your ComfyUI installation path.")
        print("Example: D:\\StableDiffusion\\ComfyUI")
        
        skip = input("\nDo you want to scan local ComfyUI installation? (y/n) [y]: ").strip().lower() or 'y'
        
        if skip != 'y':
            return False
        
        while True:
            path = input("Enter ComfyUI installation path: ").strip().strip('"').strip("'")
            
            if not path:
                return False
            
            if self.set_comfyui_path(path):
                return True
            
            retry = input("Try again? (y/n): ").strip().lower()
            if retry != 'y':
                return False
    
    def scan_builtin_nodes(self) -> Set[str]:
        """
        Scan ComfyUI core files for built-in node classes.
        
        Returns:
            Set of built-in node class names
        """
        if not self.comfyui_path:
            return set()
        
        print("\n🔍 Scanning for built-in nodes...")
        
        builtin_files = [
            self.comfyui_path / "nodes.py",
            self.comfyui_path / "comfy_extras" / "nodes_custom_sampler.py",
            self.comfyui_path / "comfy_extras" / "nodes_post_processing.py",
            self.comfyui_path / "comfy_extras" / "nodes_upscale_model.py",
            self.comfyui_path / "comfy_extras" / "nodes_mask.py",
            self.comfyui_path / "comfy_extras" / "nodes_compositing.py",
            self.comfyui_path / "comfy_extras" / "nodes_rebatch.py",
            self.comfyui_path / "comfy_extras" / "nodes_model_advanced.py",
            self.comfyui_path / "comfy_extras" / "nodes_model_merging.py",
            self.comfyui_path / "comfy_extras" / "nodes_images.py",
            self.comfyui_path / "comfy_extras" / "nodes_audio.py",
            self.comfyui_path / "comfy_extras" / "nodes_video_model.py",
            self.comfyui_path / "comfy_extras" / "nodes_cond.py",
            self.comfyui_path / "comfy_extras" / "nodes_freelunch.py",
            self.comfyui_path / "comfy_extras" / "nodes_flux.py",
            self.comfyui_path / "comfy_extras" / "nodes_differential_diffusion.py",
            self.comfyui_path / "comfy_extras" / "nodes_align_your_steps.py",
            self.comfyui_path / "comfy_extras" / "nodes_hydit.py",
            self.comfyui_path / "comfy_extras" / "nodes_hunyuan.py",
            self.comfyui_path / "comfy_extras" / "nodes_sd3.py",
            self.comfyui_path / "comfy_extras" / "nodes_clip_sdxl.py",
            self.comfyui_path / "comfy_extras" / "nodes_photomaker.py",
            self.comfyui_path / "comfy_extras" / "nodes_stable_cascade.py",
            self.comfyui_path / "comfy_extras" / "nodes_sag.py",
            self.comfyui_path / "comfy_extras" / "nodes_perpneg.py",
            self.comfyui_path / "comfy_extras" / "nodes_tomesd.py",
            self.comfyui_path / "comfy_extras" / "nodes_model_downscale.py",
        ]
        
        for file_path in builtin_files:
            if file_path.exists():
                nodes = self._extract_node_classes(file_path)
                self.builtin_nodes.update(nodes)
        
        # Add known built-in nodes that may not be detected by scanning
        # These are core ComfyUI nodes that are always available
        known_builtin = {
            'PrimitiveNode',  # Value holder/passthrough node
            'Reroute',        # Connection routing node
            'Note',           # Comment/annotation node
        }
        self.builtin_nodes.update(known_builtin)
        
        print(f"✓ Found {len(self.builtin_nodes)} built-in node classes")
        return self.builtin_nodes
    
    def scan_custom_nodes(self) -> Dict[str, str]:
        """
        Scan custom_nodes directory for custom node classes.
        
        Returns:
            Dictionary mapping class names to their repository paths
        """
        if not self.comfyui_path:
            return {}
        
        custom_nodes_dir = self.comfyui_path / "custom_nodes"
        
        if not custom_nodes_dir.exists():
            print("⚠ custom_nodes directory not found")
            return {}
        
        print("\n🔍 Scanning custom nodes...")
        
        # Scan each subdirectory in custom_nodes
        for repo_dir in custom_nodes_dir.iterdir():
            if not repo_dir.is_dir():
                continue
            
            if repo_dir.name.startswith('.'):
                continue
            
            # Scan all Python files in this repo
            for py_file in repo_dir.rglob("*.py"):
                # Skip __pycache__ and other non-init __ files, but keep __init__.py
                if py_file.name.startswith('__') and py_file.name != '__init__.py':
                    continue
                
                try:
                    nodes = self._extract_node_classes(py_file)
                    for node_class in nodes:
                        self.custom_nodes[node_class] = str(repo_dir.name)
                    
                    # Also extract NODE_CLASS_MAPPINGS if present (especially in __init__.py)
                    mappings = self._extract_node_mappings(py_file)
                    for display_name, class_name in mappings.items():
                        # Store both the display name and class name
                        self.custom_nodes[display_name] = str(repo_dir.name)
                        self.custom_nodes[class_name] = str(repo_dir.name)
                except:
                    pass
        
        print(f"✓ Found {len(self.custom_nodes)} custom node classes in {len(set(self.custom_nodes.values()))} repositories")
        return self.custom_nodes
    
    def _extract_node_classes(self, file_path: Path) -> Set[str]:
        """
        Extract node class names from a Python file.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Set of class names found in the file
        """
        classes = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content)
            
            # Look for class definitions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.add(node.name)
            
        except Exception as e:
            # Silently skip files that can't be parsed
            pass
        
        return classes
    
    def _extract_node_mappings(self, file_path: Path) -> Dict[str, str]:
        """
        Extract NODE_CLASS_MAPPINGS from a Python file.
        This maps display names to class names.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Dictionary mapping display names to class names
        """
        mappings = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content)
            
            # Look for NODE_CLASS_MAPPINGS assignment
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "NODE_CLASS_MAPPINGS":
                            # Try to extract the dictionary
                            if isinstance(node.value, ast.Dict):
                                for key, value in zip(node.value.keys, node.value.values):
                                    if isinstance(key, ast.Constant) and isinstance(value, ast.Name):
                                        display_name = key.value
                                        class_name = value.id
                                        mappings[display_name] = class_name
            
        except Exception as e:
            # Silently skip files that can't be parsed
            pass
        
        return mappings
    
    def scan_all(self, force_rescan: bool = False) -> tuple[Set[str], Dict[str, str]]:
        """
        Scan both built-in and custom nodes, using cache if available.
        
        Args:
            force_rescan: Force a full rescan even if cache is valid
            
        Returns:
            Tuple of (builtin_nodes, custom_nodes)
        """
        if not self.comfyui_path:
            if not self.prompt_for_path():
                return set(), {}
        
        # Try to load from cache if enabled
        if self.use_cache and not force_rescan:
            # Check if custom_nodes directory has changed
            if not self.cache.has_changed(self.comfyui_path):
                # Try to load cached results
                cached_results = self.cache.load_scan_results()
                if cached_results:
                    self.builtin_nodes, self.custom_nodes = cached_results
                    metadata = self.cache.get_metadata()
                    if metadata:
                        print(f"✓ Loaded from cache: {metadata['builtin_count']} built-in, "
                              f"{metadata['custom_count']} custom nodes from {metadata['total_repos']} repos")
                    else:
                        print(f"✓ Loaded from cache: {len(self.builtin_nodes)} built-in, "
                              f"{len(self.custom_nodes)} custom nodes")
                    return self.builtin_nodes, self.custom_nodes
                else:
                    print("⚠ Cache exists but failed to load, rescanning...")
            else:
                print("📁 Custom nodes directory changed, rescanning...")
        
        # Perform full scan
        print("🔍 Scanning ComfyUI installation...")
        self.scan_builtin_nodes()
        self.scan_custom_nodes()
        
        # Save to cache if enabled
        if self.use_cache:
            self.cache.save_scan_results(self.builtin_nodes, self.custom_nodes, self.comfyui_path)
            print("💾 Scan results cached")
        
        return self.builtin_nodes, self.custom_nodes
    
    def classify_node(self, class_name: str) -> str:
        """
        Classify a node as built-in, custom, or unknown.
        
        Args:
            class_name: Node class name (may include display name with parentheses)
            
        Returns:
            'builtin', 'custom', or 'unknown'
        """
        # Try exact match first
        if class_name in self.builtin_nodes:
            return 'builtin'
        elif class_name in self.custom_nodes:
            return 'custom'
        
        # If class_name has parentheses (display name format), try to find the actual class
        if '(' in class_name and ')' in class_name:
            # Extract repo hint from parentheses
            repo_hint = class_name[class_name.rfind('(') + 1:class_name.rfind(')')].lower()
            base_name = class_name[:class_name.rfind('(')].strip()
            
            # Search for nodes from that repo
            for node_class, repo in self.custom_nodes.items():
                if repo_hint in repo.lower():
                    # Check if the base name matches (case-insensitive, ignoring spaces)
                    node_clean = node_class.lower().replace('_', '').replace(' ', '')
                    base_clean = base_name.lower().replace('_', '').replace(' ', '')
                    
                    if base_clean in node_clean or node_clean in base_clean:
                        # Store this mapping for future lookups
                        self.custom_nodes[class_name] = repo
                        return 'custom'
        
        return 'unknown'
    
    def get_custom_node_repo(self, class_name: str) -> Optional[str]:
        """
        Get the repository name for a custom node.
        
        Args:
            class_name: Node class name
            
        Returns:
            Repository name or None if not found
        """
        return self.custom_nodes.get(class_name)
    
    def save_scan_results(self, output_path: str):
        """
        Save scan results to a file.
        
        Args:
            output_path: Path to save results
        """
        data = {
            "comfyui_path": str(self.comfyui_path) if self.comfyui_path else None,
            "builtin_nodes": sorted(list(self.builtin_nodes)),
            "custom_nodes": {k: v for k, v in sorted(self.custom_nodes.items())},
            "summary": {
                "total_builtin": len(self.builtin_nodes),
                "total_custom": len(self.custom_nodes),
                "total_repos": len(set(self.custom_nodes.values()))
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"\n💾 Scan results saved to: {output_path}")


def main():
    """Example usage."""
    import sys
    
    scanner = ComfyUIScanner()
    
    if len(sys.argv) > 1:
        scanner.set_comfyui_path(sys.argv[1])
    else:
        scanner.prompt_for_path()
    
    if scanner.comfyui_path:
        builtin, custom = scanner.scan_all()
        
        print(f"\n📊 Summary:")
        print(f"  Built-in nodes: {len(builtin)}")
        print(f"  Custom nodes: {len(custom)}")
        print(f"  Custom repos: {len(set(custom.values()))}")
        
        # Save results
        scanner.save_scan_results("comfyui_scan.json")


if __name__ == "__main__":
    main()
