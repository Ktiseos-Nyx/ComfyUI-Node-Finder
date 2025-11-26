"""
Static Node Name Analyzer

Analyzes Python code to extract dynamically generated node names WITHOUT executing code.
Uses AST parsing and symbolic evaluation to trace through imports and function calls.

Example: Resolving rgthree's dynamic names
    NAME = get_name("Context Switch")
    -> traces to constants.py
    -> finds get_name() returns '{} ({})'.format(name, NAMESPACE)
    -> finds NAMESPACE = 'rgthree'
    -> resolves to "Context Switch (rgthree)"
"""

import ast
from pathlib import Path
from typing import Dict, Optional, Set, Any, List, Tuple


class StaticNodeAnalyzer:
    """Statically analyze Python code to extract node names without execution."""
    
    def __init__(self, repo_path: Path):
        """
        Initialize analyzer for a custom node repository.
        
        Args:
            repo_path: Path to the custom node repository directory
        """
        self.repo_path = repo_path
        self.module_cache: Dict[str, ast.Module] = {}  # Cache parsed AST modules
        self.constant_cache: Dict[Tuple[str, str], Any] = {}  # Cache resolved constants
        self.import_map: Dict[Tuple[str, str], Path] = {}  # Maps (file, name) -> imported file path
        
    def extract_node_mappings(self, init_file: Path) -> Dict[str, str]:
        """
        Extract NODE_CLASS_MAPPINGS from __init__.py using static analysis.
        
        Args:
            init_file: Path to __init__.py file
            
        Returns:
            Dictionary mapping display names to class names
        """
        mappings = {}
        
        try:
            # Parse the __init__.py file
            tree = self._parse_file(init_file)
            if not tree:
                return mappings
            
            # First, build the import map for this file
            self._extract_imports(tree, init_file)
            
            # Find NODE_CLASS_MAPPINGS assignment
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "NODE_CLASS_MAPPINGS":
                            # Found it! Now resolve the dictionary
                            mappings = self._resolve_dict(node.value, init_file)
                            break
            
        except Exception as e:
            print(f"      Static analysis failed: {e}")
        
        return mappings
    
    def _extract_imports(self, tree: ast.Module, context_file: Path) -> None:
        """
        Extract all imports from a module and build the import map.
        
        Args:
            tree: Parsed AST module
            context_file: File being analyzed
        """
        for node in ast.walk(tree):
            # Handle: from .module import Name
            if isinstance(node, ast.ImportFrom):
                module_name = node.module or ''
                level = node.level  # Number of dots (relative import level)
                
                # Resolve relative import to actual file path
                if level > 0:  # Relative import (e.g., from .py.context_switch import ...)
                    base_path = context_file.parent
                    for _ in range(level - 1):
                        base_path = base_path.parent
                    
                    # Convert module path to file path
                    if module_name:
                        module_parts = module_name.split('.')
                        module_path = base_path / '/'.join(module_parts)
                        
                        # Try .py file or __init__.py in directory
                        if (module_path.with_suffix('.py')).exists():
                            imported_file = module_path.with_suffix('.py')
                        elif (module_path / '__init__.py').exists():
                            imported_file = module_path / '__init__.py'
                        else:
                            continue
                        
                        # Map each imported name to the file
                        for alias in node.names:
                            name = alias.asname if alias.asname else alias.name
                            self.import_map[(str(context_file), name)] = imported_file
            
            # Handle: import module
            # TODO: Add support for absolute imports if needed
    
    def _parse_file(self, file_path: Path) -> Optional[ast.Module]:
        """
        Parse a Python file into an AST, with caching.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            Parsed AST module or None if parsing fails
        """
        file_key = str(file_path)
        
        if file_key in self.module_cache:
            return self.module_cache[file_key]
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            tree = ast.parse(content)
            self.module_cache[file_key] = tree
            return tree
            
        except Exception:
            return None
    
    def _resolve_dict(self, node: ast.AST, context_file: Path) -> Dict[str, str]:
        """
        Resolve a dictionary AST node to actual key-value pairs.
        
        Args:
            node: AST node representing a dictionary
            context_file: File where this node appears (for resolving imports)
            
        Returns:
            Resolved dictionary mapping display names to class names
        """
        result = {}
        
        if isinstance(node, ast.Dict):
            # Static dictionary: {key: value, ...}
            for key, value in zip(node.keys, node.values):
                resolved_key = self._resolve_value(key, context_file)
                
                # For values that are just class names (Name nodes), use the name directly
                if isinstance(value, ast.Name):
                    resolved_value = value.id  # Just use the class name string
                else:
                    resolved_value = self._resolve_value(value, context_file)
                
                if isinstance(resolved_key, str) and isinstance(resolved_value, str):
                    result[resolved_key] = resolved_value
        
        # TODO: Handle dict comprehensions, function calls that return dicts, etc.
        
        return result
    
    def _resolve_value(self, node: ast.AST, context_file: Path) -> Any:
        """
        Resolve an AST node to its actual value through static analysis.
        
        Args:
            node: AST node to resolve
            context_file: File where this node appears
            
        Returns:
            Resolved value (str, int, etc.) or the node itself if unresolvable
        """
        # Constant values (strings, numbers, etc.)
        if isinstance(node, ast.Constant):
            return node.value
        
        # Variable names - try to resolve them
        if isinstance(node, ast.Name):
            return self._resolve_name(node.id, context_file)
        
        # Attribute access (e.g., module.CONSTANT)
        if isinstance(node, ast.Attribute):
            return self._resolve_attribute(node, context_file)
        
        # Function calls (e.g., get_name("Context Switch"))
        if isinstance(node, ast.Call):
            return self._resolve_call(node, context_file)
        
        # TODO: Handle more node types (BinOp, JoinedStr for f-strings, etc.)
        
        return None
    
    def _resolve_name(self, name: str, context_file: Path) -> Any:
        """
        Resolve a variable name to its value.
        
        Args:
            name: Variable name to resolve
            context_file: File where the name appears
            
        Returns:
            Resolved value or None
        """
        # Check cache first
        cache_key = (str(context_file), name)
        if cache_key in self.constant_cache:
            return self.constant_cache[cache_key]
        
        # Parse the file and look for the assignment
        tree = self._parse_file(context_file)
        if not tree:
            return None
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        # Found the assignment!
                        value = self._resolve_value(node.value, context_file)
                        self.constant_cache[cache_key] = value
                        return value
        
        return None
    
    def _resolve_attribute(self, node: ast.Attribute, context_file: Path) -> Any:
        """
        Resolve attribute access (e.g., RgthreeContextSwitch.NAME or constants.NAMESPACE).
        
        Args:
            node: Attribute AST node
            context_file: File where this appears
            
        Returns:
            Resolved value or None
        """
        # Handle ClassName.ATTRIBUTE (e.g., RgthreeContextSwitch.NAME)
        if isinstance(node.value, ast.Name):
            class_name = node.value.id
            attr_name = node.attr
            
            # Find the class definition (might be in imported file)
            class_def = self._find_class(class_name, context_file)
            if class_def:
                # Determine which file the class is actually in
                import_key = (str(context_file), class_name)
                actual_file = self.import_map.get(import_key, context_file)
                
                # Look for the attribute assignment in the class
                for item in class_def.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == attr_name:
                                # Found it! Resolve the value in the context of the actual file
                                return self._resolve_value(item.value, actual_file)
        
        # TODO: Handle module.attribute (imports)
        return None
    
    def _find_class(self, class_name: str, context_file: Path) -> Optional[ast.ClassDef]:
        """
        Find a class definition in the current file or imported modules.
        
        Args:
            class_name: Name of the class to find
            context_file: File to search in
            
        Returns:
            ClassDef AST node or None
        """
        # Search in current file first
        tree = self._parse_file(context_file)
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    return node
        
        # Check if this class was imported
        import_key = (str(context_file), class_name)
        if import_key in self.import_map:
            imported_file = self.import_map[import_key]
            
            # Parse the imported file
            imported_tree = self._parse_file(imported_file)
            if imported_tree:
                # Extract imports from this file too!
                self._extract_imports(imported_tree, imported_file)
                
                for node in ast.walk(imported_tree):
                    if isinstance(node, ast.ClassDef) and node.name == class_name:
                        return node
        
        return None
    
    def _resolve_call(self, node: ast.Call, context_file: Path) -> Any:
        """
        Resolve a function call by tracing the function definition.
        
        Args:
            node: Call AST node
            context_file: File where this call appears
            
        Returns:
            Resolved return value or None
        """
        # Get the function name
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            
            # Find the function definition
            func_result = self._find_function(func_name, context_file)
            if not func_result:
                return None
            
            func_def, func_file = func_result
            
            # Resolve the arguments
            args = [self._resolve_value(arg, context_file) for arg in node.args]
            
            # Symbolically execute the function with these args (in its own file context)
            return self._execute_function(func_def, args, func_file)
        
        # TODO: Handle method calls, imported functions, etc.
        return None
    
    def _find_function(self, func_name: str, context_file: Path) -> Optional[Tuple[ast.FunctionDef, Path]]:
        """
        Find a function definition in the current file or imported modules.
        
        Args:
            func_name: Name of the function to find
            context_file: File to search in
            
        Returns:
            Tuple of (FunctionDef AST node, file path) or None
        """
        # Search in current file first
        tree = self._parse_file(context_file)
        if tree:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    return (node, context_file)
        
        # Check if this function was imported
        import_key = (str(context_file), func_name)
        if import_key in self.import_map:
            imported_file = self.import_map[import_key]
            
            # Parse the imported file
            imported_tree = self._parse_file(imported_file)
            if imported_tree:
                # Extract imports from this file too!
                self._extract_imports(imported_tree, imported_file)
                
                for node in ast.walk(imported_tree):
                    if isinstance(node, ast.FunctionDef) and node.name == func_name:
                        return (node, imported_file)
        
        return None
    
    def _execute_function(self, func_def: ast.FunctionDef, args: List[Any], context_file: Path) -> Any:
        """
        Symbolically execute a function with given arguments.
        
        Args:
            func_def: Function definition AST node
            args: List of argument values
            context_file: File where function is defined
            
        Returns:
            Resolved return value or None
        """
        # Build a symbol table mapping parameter names to argument values
        symbols = {}
        for param, arg in zip(func_def.args.args, args):
            symbols[param.arg] = arg
        
        # Walk through the function body looking for return statements
        for node in ast.walk(func_def):
            if isinstance(node, ast.Return) and node.value:
                # Resolve the return value with our symbol table
                return self._resolve_with_symbols(node.value, symbols, context_file)
        
        return None
    
    def _resolve_with_symbols(self, node: ast.AST, symbols: Dict[str, Any], context_file: Path) -> Any:
        """
        Resolve an AST node using a symbol table (for function parameters).
        
        Args:
            node: AST node to resolve
            symbols: Symbol table mapping names to values
            context_file: File context
            
        Returns:
            Resolved value or None
        """
        # Check if it's a variable in our symbol table
        if isinstance(node, ast.Name) and node.id in symbols:
            return symbols[node.id]
        
        # Handle string formatting: '{} ({})'.format(name, NAMESPACE)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == 'format':
                    # Get the format string
                    format_str = self._resolve_with_symbols(node.func.value, symbols, context_file)
                    if isinstance(format_str, str):
                        # Get the format arguments
                        format_args = [self._resolve_with_symbols(arg, symbols, context_file) for arg in node.args]
                        
                        # Apply the formatting
                        try:
                            return format_str.format(*format_args)
                        except:
                            pass
        
        # Fall back to regular resolution
        return self._resolve_value(node, context_file)


# Example usage:
if __name__ == "__main__":
    # Scan all custom nodes
    custom_nodes_dir = Path("D:/StableDiffusion/ComfyUI/custom_nodes")
    
    print(f"Scanning custom nodes in: {custom_nodes_dir}\n")
    
    total_mappings = {}
    repos_scanned = 0
    repos_with_mappings = 0
    
    for repo_dir in custom_nodes_dir.iterdir():
        if not repo_dir.is_dir():
            continue
        
        if repo_dir.name.startswith('.'):
            continue
        
        init_file = repo_dir / "__init__.py"
        if not init_file.exists():
            continue
        
        repos_scanned += 1
        
        # Analyze this repository
        analyzer = StaticNodeAnalyzer(repo_dir)
        mappings = analyzer.extract_node_mappings(init_file)
        
        if mappings:
            repos_with_mappings += 1
            print(f"✓ {repo_dir.name}: {len(mappings)} nodes")
            total_mappings.update(mappings)
            
            # Show first 3 nodes as examples
            for i, (display_name, class_name) in enumerate(mappings.items()):
                if i < 3:
                    print(f"    {display_name} -> {class_name}")
                elif i == 3:
                    print(f"    ... and {len(mappings) - 3} more")
                    break
            print()
    
    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Repositories scanned: {repos_scanned}")
    print(f"  Repositories with mappings: {repos_with_mappings}")
    print(f"  Total node mappings found: {len(total_mappings)}")
    print(f"{'='*60}")
